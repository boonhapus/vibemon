"""Run the Vibemon backend API and frontend dev servers together."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import argparse
import atexit
import contextlib
import ipaddress
import logging
import os
import re
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request

import structlog

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
_FRONTEND_PORT = 5173
_READY_TIMEOUT_S = 120.0
_READY_POLL_S = 0.25
_WINDOWS_IPV4_RE = re.compile(r"IPv4[^:]*:\s*([\d.]+)")

if sys.platform == "win32":
    from ctypes import wintypes
    import ctypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_ulonglong),
            ("WriteOperationCount", ctypes.c_ulonglong),
            ("OtherOperationCount", ctypes.c_ulonglong),
            ("ReadTransferCount", ctypes.c_ulonglong),
            ("WriteTransferCount", ctypes.c_ulonglong),
            ("OtherTransferCount", ctypes.c_ulonglong),
        ]

    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    _JobObjectExtendedLimitInformation = 9
    _CREATE_BREAKAWAY_FROM_JOB = 0x01000000

    def _create_kill_on_close_job() -> int:
        job = _kernel32.CreateJobObjectW(None, None)
        if not job:
            raise OSError("CreateJobObjectW failed")

        info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not _kernel32.SetInformationJobObject(
            job,
            _JobObjectExtendedLimitInformation,
            ctypes.byref(info),
            ctypes.sizeof(info),
        ):
            _kernel32.CloseHandle(job)
            raise OSError("SetInformationJobObject failed")
        return job

    def _assign_to_job(job: int, process: subprocess.Popen[object]) -> None:
        if not _kernel32.AssignProcessToJobObject(job, process._handle):
            raise OSError("AssignProcessToJobObject failed")

    def _close_job(job: int) -> None:
        _kernel32.CloseHandle(job)


def _configure_dev_logging() -> structlog.stdlib.BoundLogger:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
            structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty()),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger("dev_stack")


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        raise SystemExit("Cannot run an empty command.")
    executable = shutil.which(command[0])
    if executable is None:
        raise SystemExit(f"Could not find '{command[0]}' on PATH. Install it or add it to PATH, then retry.")
    return [executable, *command[1:]]


def _spawn(
    command: list[str],
    *,
    cwd: Path,
    job: int | None = None,
) -> subprocess.Popen[object]:
    """Start a child process; on Windows keep it out of the console Ctrl+C group."""
    resolved = _resolve_command(command)
    kwargs: dict[str, object] = {}
    if sys.platform == "win32":
        # Ctrl+C should stop dev_stack only; we tear down children explicitly.
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_BREAKAWAY_FROM_JOB
    process = subprocess.Popen(
        resolved,
        cwd=cwd,
        env=os.environ.copy(),
        **kwargs,
    )
    if job is not None:
        with contextlib.suppress(OSError):
            _assign_to_job(job, process)
    return process


def _frontend_scheme() -> str:
    cert_dir = FRONTEND / ".certs"
    has_dev_cert = (cert_dir / "dev-cert.pem").is_file() and (cert_dir / "dev-key.pem").is_file()
    return "https" if has_dev_cert else "http"


def _frontend_origins() -> tuple[str, ...]:
    scheme = _frontend_scheme()
    localhost = (
        f"{scheme}://localhost:{_FRONTEND_PORT}",
        f"{scheme}://127.0.0.1:{_FRONTEND_PORT}",
    )
    if scheme == "https":
        return (*localhost, f"http://localhost:{_FRONTEND_PORT}")
    return localhost


def _tailscale_ipv4_addresses() -> set[str]:
    executable = shutil.which("tailscale")
    if executable is None:
        return set()
    try:
        result = subprocess.run(
            [executable, "ip", "-4"],
            capture_output=True,
            text=True,
            check=False,
            timeout=2,
        )
    except OSError, subprocess.TimeoutExpired:
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _windows_ipv4_addresses() -> set[str]:
    try:
        result = subprocess.run(["ipconfig"], capture_output=True, text=True, check=False, timeout=3)
    except OSError, subprocess.TimeoutExpired:
        return set()
    if result.returncode != 0:
        return set()
    return {
        match.group(1) for match in _WINDOWS_IPV4_RE.finditer(result.stdout) if not match.group(1).startswith("127.")
    }


def _unix_ipv4_addresses() -> set[str]:
    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except OSError, subprocess.TimeoutExpired:
        return set()
    if result.returncode != 0:
        return set()
    found: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split()
        for part in parts:
            if "/" not in part or part.startswith("inet"):
                continue
            ip = part.split("/", 1)[0]
            if not ip.startswith("127."):
                found.add(ip)
    return found


def _discover_ipv4_addresses() -> list[str]:
    found = _tailscale_ipv4_addresses()
    if sys.platform == "win32":
        found.update(_windows_ipv4_addresses())
    else:
        found.update(_unix_ipv4_addresses())

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if not ip.startswith("127."):
                found.add(ip)
    except OSError:
        pass

    return sorted(found, key=ipaddress.ip_address)


def _frontend_urls() -> list[str]:
    scheme = _frontend_scheme()
    urls = [
        f"{scheme}://localhost:{_FRONTEND_PORT}",
        f"{scheme}://127.0.0.1:{_FRONTEND_PORT}",
    ]
    seen_hosts = {"localhost", "127.0.0.1"}
    for ip in _discover_ipv4_addresses():
        if ip in seen_hosts:
            continue
        seen_hosts.add(ip)
        urls.append(f"{scheme}://{ip}:{_FRONTEND_PORT}")
    return urls


def _probe_url(url: str, *, timeout: float = 1.0) -> bool:
    request = urllib.request.Request(url, method="GET")
    context = None
    if url.startswith("https://"):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return 200 <= response.status < 500
    except urllib.error.URLError, TimeoutError, OSError:
        return False


def _first_live_frontend_origin() -> str | None:
    for origin in _frontend_origins():
        if _probe_url(f"{origin}/"):
            return origin
    return None


def _wait_for_ready(
    log: structlog.stdlib.BoundLogger,
    *,
    backend_host: str,
    backend_port: int,
    processes: list[subprocess.Popen[object]],
    stop_requested: Callable[[], bool],
) -> int | None:
    """Return a child exit code when a server dies before becoming ready."""
    backend_url = f"http://{backend_host}:{backend_port}"
    backend_ready = False
    frontend_origin: str | None = None
    deadline = time.monotonic() + _READY_TIMEOUT_S

    while time.monotonic() < deadline:
        if stop_requested():
            return None

        for process in processes:
            code = process.poll()
            if code is not None:
                return code

        if not backend_ready:
            backend_ready = _probe_url(f"{backend_url}/api/healthz")
        if frontend_origin is None:
            frontend_origin = _first_live_frontend_origin()

        if backend_ready and frontend_origin is not None:
            log.info("dev_stack_ready", frontend=_frontend_urls())
            return None

        time.sleep(_READY_POLL_S)

    log.warning(
        "dev_stack_ready_timeout",
        backend=backend_url,
        frontend=frontend_origin,
        timeout_s=_READY_TIMEOUT_S,
    )
    return None


def _kill_process_tree(process: subprocess.Popen[object]) -> None:
    if process.poll() is not None:
        return

    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            capture_output=True,
        )
        return

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except ProcessLookupError, PermissionError, OSError:
        process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError, PermissionError, OSError:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    args = parser.parse_args()

    log = _configure_dev_logging()

    backend_cmd = [
        sys.executable,
        str(BACKEND / "scripts" / "run_dev_uvicorn.py"),
        "--host",
        args.backend_host,
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = ["pnpm", "--silent", "dev", "--", "--logLevel", "warn"]

    log.info(
        "dev_stack_starting",
        backend=f"http://{args.backend_host}:{args.backend_port}",
        frontend="https://localhost:5173",
        hint="Press Ctrl+C to stop both servers.",
    )

    job: int | None = None
    if sys.platform == "win32":
        try:
            job = _create_kill_on_close_job()
            atexit.register(_close_job, job)
        except OSError:
            job = None

    backend = _spawn(backend_cmd, cwd=BACKEND, job=job)
    frontend = _spawn(frontend_cmd, cwd=FRONTEND, job=job)
    processes = [backend, frontend]
    exit_code = 0
    stop_requested = False

    def _shutdown_children() -> None:
        for process in processes:
            _kill_process_tree(process)

    def _request_stop(_signum: int, _frame: object | None) -> None:
        nonlocal stop_requested
        if stop_requested:
            return
        stop_requested = True
        log.info("dev_stack_stopping")
        _shutdown_children()

    signal.signal(signal.SIGINT, _request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _request_stop)

    try:
        early_exit = _wait_for_ready(
            log,
            backend_host=args.backend_host,
            backend_port=args.backend_port,
            processes=processes,
            stop_requested=lambda: stop_requested,
        )
        if early_exit is not None:
            log.error("dev_stack_child_exited", exit_code=early_exit)
            return early_exit

        while not stop_requested:
            for process in processes:
                code = process.poll()
                if code is not None:
                    log.error("dev_stack_child_exited", exit_code=code)
                    exit_code = code if code is not None else 1
                    return exit_code
            time.sleep(0.5)
    except KeyboardInterrupt:
        _request_stop(signal.SIGINT, None)
    finally:
        _shutdown_children()

    return 0 if stop_requested else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
