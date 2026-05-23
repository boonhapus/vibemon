"""Static content loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.content.moves import MoveContentIssue, MoveContentLoadResult, load_provider_moves

if TYPE_CHECKING:
    from app import schema

CONTENT_DIR = Path(__file__).parent / "moves"


def load_universal_moves() -> tuple[schema.Move, ...]:
    """Load universal moves from JSON content."""
    result = load_provider_moves(CONTENT_DIR / "universal.json")
    if result.has_errors:
        issues = "; ".join(i.message for i in result.issues[:5])
        raise ValueError(f"Universal move content errors: {issues}")
    return result.moves


__all__ = [
    "CONTENT_DIR",
    "MoveContentIssue",
    "MoveContentLoadResult",
    "load_provider_moves",
    "load_universal_moves",
]
