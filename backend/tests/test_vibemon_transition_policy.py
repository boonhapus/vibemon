import datetime as dt

import pytest

from app import errors, types
from app.policies import vibemon_transitions


def test_review_deadline_passed_legal_and_illegal() -> None:
    now = dt.datetime(2026, 5, 18, 12, 0, tzinfo=dt.UTC)
    assert vibemon_transitions.review_deadline_passed(timeout_at=now - dt.timedelta(seconds=1), now=now)
    assert vibemon_transitions.review_deadline_passed(timeout_at=now, now=now)
    assert not vibemon_transitions.review_deadline_passed(timeout_at=now + dt.timedelta(seconds=1), now=now)


@pytest.mark.parametrize(
    ("status", "is_legal"),
    [
        (types.CandidateReviewStatusT.PENDING.value, True),
        (types.CandidateReviewStatusT.ADOPTED.value, False),
        (types.CandidateReviewStatusT.REJECTED.value, False),
        (types.CandidateReviewStatusT.TIMED_OUT.value, False),
    ],
)
def test_pending_review_status_matrix(status: str, is_legal: bool) -> None:
    if is_legal:
        vibemon_transitions.require_pending_review_status(status)
        return
    with pytest.raises(errors.CandidateReviewUnavailable):
        vibemon_transitions.require_pending_review_status(status)


def test_select_adoption_slot_open_party_uses_next_free_slot() -> None:
    assert vibemon_transitions.select_adoption_slot(owned_count=2, used_slots={0, 1}, release_slot=None) == 2


def test_select_adoption_slot_full_party_requires_release() -> None:
    with pytest.raises(errors.PartyFull, match="releasing one party Vibemon"):
        vibemon_transitions.select_adoption_slot(owned_count=6, used_slots={0, 1, 2, 3, 4, 5}, release_slot=None)


def test_select_adoption_slot_full_party_accepts_release_slot() -> None:
    assert (
        vibemon_transitions.select_adoption_slot(
            owned_count=6,
            used_slots={0, 1, 2, 3, 4, 5},
            release_slot=3,
        )
        == 3
    )
