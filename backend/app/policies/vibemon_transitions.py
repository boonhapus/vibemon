"""Transition policy checks for Vibemon service commands."""

from __future__ import annotations

import datetime as dt

from app import errors, types


def review_deadline_passed(*, timeout_at: dt.datetime, now: dt.datetime) -> bool:
    """Return whether a pending candidate review is already expired."""
    normalized_timeout = _as_utc(timeout_at)
    normalized_now = _as_utc(now)
    return normalized_timeout <= normalized_now


def require_pending_review_status(status: str) -> None:
    """Ensure command actions only run from pending candidate-review state."""
    if status != types.CandidateReviewStatusT.PENDING.value:
        raise errors.CandidateReviewUnavailable("No pending candidate review exists for this trainer and Vibemon.")


def select_adoption_slot(
    *,
    owned_count: int,
    used_slots: set[int],
    release_slot: int | None,
) -> int:
    """Decide adoption slot based on party occupancy and optional release slot."""
    if owned_count < 6:
        return next(slot for slot in range(6) if slot not in used_slots)
    if release_slot is None:
        raise errors.PartyFull("Adoption requires releasing one party Vibemon.")
    return release_slot


def _as_utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)
