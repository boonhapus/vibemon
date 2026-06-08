"""Filesystem anchors for the cutout tool."""

import pathlib

TOOL_DIR = pathlib.Path(__file__).resolve().parent
STATIC_DIR = TOOL_DIR / "static"
REPO_ROOT = TOOL_DIR.parents[2]
