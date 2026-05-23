from __future__ import annotations

import datetime as dt

import pytest

from app.core.errors import CandidateReviewUnavailable
from app.domains.adoption import policy, schema
from app.domains.adoption.types import CandidateReviewStatusT


def test_review_deadline_compares_naive_and_aware_times_as_utc() -> None:
    timeout_at = dt.datetime(2026, 5, 19, 12, 0)
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)

    assert policy.review_deadline_passed(timeout_at=timeout_at, now=now)


def test_pending_review_policy_rejects_resolved_status() -> None:
    with pytest.raises(CandidateReviewUnavailable):
        policy.require_pending_review_status(CandidateReviewStatusT.REJECTED.value)


def test_candidate_review_label_copy_is_adoption_owned() -> None:
    assert schema.candidate_review_status_label(CandidateReviewStatusT.TIMED_OUT) == "Timed out"
