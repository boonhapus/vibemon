"""Last.fm API response field validators and reusable annotated types."""

from typing import Annotated, Any
import uuid

from pydantic import BeforeValidator


def ensure_valid_mbid(value: Any) -> str | None:
    """Musicbrainz IDs are uuids."""
    try:
        value = uuid.UUID(value)
    except TypeError, AttributeError, ValueError:
        return None

    return str(value)


def ensure_valid_duration(value: Any) -> float | None:
    """Last.fm is community-driven, sometimes tracks are in ms or s."""
    if value is None:
        return value

    value = float(value)

    if value >= 10_000:
        value = value / 1_000

    return value


MBID = Annotated[str | None, BeforeValidator(ensure_valid_mbid)]
Seconds = Annotated[float | None, BeforeValidator(ensure_valid_duration)]
