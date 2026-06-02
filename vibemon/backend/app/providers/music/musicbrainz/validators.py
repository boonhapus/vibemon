"""Musicbrainz API response field validators and reusable annotated types."""

from typing import Annotated, Any

from pydantic import BeforeValidator


def ensure_valid_duration(value: Any) -> float | None:
    """Convert ms to s."""
    if value is None:
        return value

    return float(value) / 1_000


Seconds = Annotated[float | None, BeforeValidator(ensure_valid_duration)]
