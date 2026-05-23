"""Gameplay availability state for Vibemon."""

from __future__ import annotations

import enum


class VibemonDispositionT(enum.StrEnum):
    """Gameplay availability state for a Vibemon."""

    OWNED = "owned"
    WILD = "wild"
    EXPIRED = "expired"
