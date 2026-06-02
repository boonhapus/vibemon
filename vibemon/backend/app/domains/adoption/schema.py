"""Adoption read-model schemas."""

import datetime as dt
import uuid

import pydantic

from app.core.ids import TrainerIdT
from app.core.schema import FrozenSchema
from app.domains.adoption.types import CandidateReviewStatusT
from app.providers import schema as providers_schema


class CandidateReviewRead(FrozenSchema):
    id: uuid.UUID
    trainer_id: TrainerIdT
    status: CandidateReviewStatusT
    shown_at: dt.datetime
    timeout_at: dt.datetime
    resolved_at: dt.datetime | None = None
    resolution: CandidateReviewStatusT | None = None
    status_label: str
    resolved_label: str | None = None
    provider_notes: tuple[providers_schema.ProviderNote, ...] = ()

    @pydantic.field_validator("shown_at", "timeout_at", "resolved_at")
    @classmethod
    def _normalize_to_utc(cls, value: dt.datetime | None) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


_CANDIDATE_REVIEW_STATUS_LABELS: dict[CandidateReviewStatusT, str] = {
    CandidateReviewStatusT.PENDING: "Pending",
    CandidateReviewStatusT.ADOPTED: "Adopted",
    CandidateReviewStatusT.REJECTED: "Rejected",
    CandidateReviewStatusT.TIMED_OUT: "Timed out",
}


def candidate_review_status_label(status: CandidateReviewStatusT) -> str:
    """Return stable player-facing copy for candidate-review status."""

    return _CANDIDATE_REVIEW_STATUS_LABELS[status]
