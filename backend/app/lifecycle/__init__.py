"""Lifecycle orchestration for Vibemon.

Use this package to drive name finalization, asset generation, and trainer
ownership transitions. Lifecycle functions perform network I/O and mutate the
``schema.Vibemon`` instance in place.
"""

from app.lifecycle.vibemon import adopt, christen, manifest

__all__ = ["adopt", "christen", "manifest"]
