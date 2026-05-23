"""Shared UTC clock primitives."""

from __future__ import annotations

from collections.abc import Callable
import datetime as dt

type Clock = Callable[[], dt.datetime]


def resolve_clock(clock: Clock | None = None) -> dt.datetime:
    now = clock() if clock is not None else dt.datetime.now(tz=dt.UTC)
    return as_utc(now)


def as_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)
