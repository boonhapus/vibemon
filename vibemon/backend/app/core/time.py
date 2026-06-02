"""Shared UTC clock primitives."""

from collections.abc import Callable
import datetime as dt

type Clock = Callable[[], dt.datetime]
"""Injectable now-source for tests and workflows."""


def resolve_clock(clock: Clock | None = None) -> dt.datetime:
    """Return the current instant in UTC, using ``clock`` when provided."""
    now = clock() if clock is not None else dt.datetime.now(tz=dt.UTC)
    return as_utc(now)


def as_utc(value: dt.datetime) -> dt.datetime:
    """Normalize naive datetimes to UTC; convert aware values to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)
