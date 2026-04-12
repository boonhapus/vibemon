#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "colorama>=0.4.6",
#   "structlog>=25.0.0",
# ]
# ///
"""
Complete setup and dev server for vibemon.

Usage:
    uv run .scripts/dev.py
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path

import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

REPO_ROOT = Path(__file__).parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

# ── tool resolution ────────────────────────────────────────────────────────────

def find_tool(name: str, fallback: Path) -> str:
    found = shutil.which(name)
    if found:
        return found
    if fallback.exists():
        return str(fallback)
    hints = {
        "uv":   "https://docs.astral.sh/uv/getting-started/installation/",
        "pnpm": "npm install -g pnpm",
    }
    log.error("tool not found", tool=name, fallback=str(fallback), install=hints.get(name))
    sys.exit(1)

home = Path.home()
uv   = find_tool("uv",   home / ".local" / "bin" / "uv")
pnpm = find_tool("pnpm", home / "AppData" / "Local" / "pnpm" / "pnpm")

# ── setup ──────────────────────────────────────────────────────────────────────

def run(cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    merged = {**os.environ, **(env or {})}
    result = subprocess.run(cmd, cwd=cwd, env=merged)
    if result.returncode != 0:
        sys.exit(result.returncode)

log.info("syncing dependencies", service="backend")
venv = BACKEND_DIR / ".venv"
if (venv / "lib64").exists() or (venv / "lib64").is_symlink():
    log.info("removing stale venv (WSL/Windows mismatch)", service="backend")
    shutil.rmtree(venv, ignore_errors=True)
run([uv, "sync", "--quiet"], BACKEND_DIR, env={"UV_LINK_MODE": "copy"})
log.info("ready", service="backend")

log.info("installing dependencies", service="frontend")
run([pnpm, "install", "--silent"], FRONTEND_DIR)
log.info("ready", service="frontend")

# ── stream output with prefix ──────────────────────────────────────────────────

def stream(proc: subprocess.Popen, service: str) -> None:
    assert proc.stdout is not None
    slog = log.bind(service=service)
    for line in proc.stdout:
        slog.info(line.rstrip())

# ── launch ─────────────────────────────────────────────────────────────────────

log.info("starting", service="backend",  url="http://localhost:8000")
log.info("starting", service="frontend", url="http://localhost:5173")

backend = subprocess.Popen(
    [uv, "run", "python", "run.py"],
    cwd=BACKEND_DIR,
    env={**os.environ, "UV_LINK_MODE": "copy"},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
frontend = subprocess.Popen(
    [pnpm, "dev"],
    cwd=FRONTEND_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

threading.Thread(target=stream, args=(backend,  "backend"),  daemon=True).start()
threading.Thread(target=stream, args=(frontend, "frontend"), daemon=True).start()

# ── cleanup ────────────────────────────────────────────────────────────────────

def shutdown(sig: int, _frame: object) -> None:
    log.info("shutting down")
    for proc in (backend, frontend):
        if proc.poll() is None:
            proc.terminate()
    for proc in (backend, frontend):
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(0)

signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)

# wait for either process to exit
backend.wait()
frontend.wait()
