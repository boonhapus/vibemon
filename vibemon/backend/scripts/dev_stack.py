"""Run the Vibemon backend API and frontend dev servers together."""

from __future__ import annotations

from pathlib import Path
import argparse
import atexit
import os
import shutil
import signal
import subprocess
import sys
import time

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

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


def _resolve_command(command: list[str]) -> list[str]:
    if not command:
        raise SystemExit("Cannot run an empty command.")
    executable = shutil.which(command[0])
    if executable is None:
        raise SystemExit(
            f"Could not find '{command[0]}' on PATH. Install it or add it to PATH, then retry."
        )
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
        kwargs["creationflags"] = (
            subprocess.CREATE_NEW_PROCESS_GROUP | _CREATE_BREAKAWAY_FROM_JOB
        )
    process = subprocess.Popen(
        resolved,
        cwd=cwd,
        env=os.environ.copy(),
        **kwargs,
    )
    if job is not None:
        try:
            _assign_to_job(job, process)
        except OSError:
            pass
    return process


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
    except (ProcessLookupError, PermissionError, OSError):
        process.terminate()

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-host", default="127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000)
    args = parser.parse_args()

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.http.app:app",
        "--reload",
        "--no-access-log",
        "--host",
        args.backend_host,
        "--port",
        str(args.backend_port),
    ]
    frontend_cmd = ["pnpm", "dev"]

    print("Starting Vibemon dev stack")
    print(f"  backend:  http://{args.backend_host}:{args.backend_port}")
    print("  frontend: https://localhost:5173 (or http if no dev cert)")
    print("Press Ctrl+C to stop both.\n")

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
        print("\nStopping dev servers...")
        _shutdown_children()

    signal.signal(signal.SIGINT, _request_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _request_stop)

    try:
        while not stop_requested:
            for process in processes:
                code = process.poll()
                if code is not None:
                    print(f"\nProcess exited with code {code}. Stopping the other server.")
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
