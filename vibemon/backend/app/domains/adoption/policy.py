"""Candidate-review transition policy."""

import datetime as dt

from app.core import errors, time
from app.domains.adoption.types import CandidateReviewStatusT


def review_deadline_passed(*, timeout_at: dt.datetime, now: dt.datetime) -> bool:
    """Return whether a pending candidate review is already expired."""

    return time.as_utc(timeout_at) <= time.as_utc(now)


def require_pending_review_status(status: str) -> None:
    """Ensure command actions only run from pending candidate-review state."""

    if status != CandidateReviewStatusT.PENDING.value:
        raise errors.CandidateReviewUnavailable("No pending candidate review exists for this trainer and Vibemon.")
