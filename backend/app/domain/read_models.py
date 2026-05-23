"""Read-model schemas exposed by service/API layers."""

from __future__ import annotations

import datetime as dt
import uuid

import pydantic

from app import brand, types
from app.domain.birth import FrozenSchema
from app.domain.move import Move
from app.domain.vibemon import Identity
from app.storage import types as ds_types


class PublicAsset(FrozenSchema):
    kind: ds_types.AssetKind
    url: str
    content_type: str
    byte_size: int
    sha256: str


class CandidateReviewRead(FrozenSchema):
    id: uuid.UUID
    trainer_id: types.TrainerIdT
    status: types.CandidateReviewStatusT
    shown_at: dt.datetime
    timeout_at: dt.datetime
    resolved_at: dt.datetime | None = None
    resolution: types.CandidateReviewStatusT | None = None
    status_label: str
    resolved_label: str | None = None

    @pydantic.field_validator("shown_at", "timeout_at", "resolved_at")
    @classmethod
    def _normalize_to_utc(cls, value: dt.datetime | None) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


_CANDIDATE_REVIEW_STATUS_LABELS: dict[types.CandidateReviewStatusT, str] = {
    types.CandidateReviewStatusT.PENDING: "Pending",
    types.CandidateReviewStatusT.ADOPTED: "Adopted",
    types.CandidateReviewStatusT.REJECTED: "Rejected",
    types.CandidateReviewStatusT.TIMED_OUT: "Timed out",
}


def candidate_review_status_label(status: types.CandidateReviewStatusT) -> str:
    """Return stable player-facing copy for candidate-review status."""

    return _CANDIDATE_REVIEW_STATUS_LABELS[status]


class TypeDefenseSummary(FrozenSchema):
    weak_to: tuple[types.VibemonTypeT, ...]
    resists: tuple[types.VibemonTypeT, ...]
    immune_to: tuple[types.VibemonTypeT, ...]


class TypeCoverageSummary(FrozenSchema):
    move_types: tuple[types.VibemonTypeT, ...]
    strong_against: tuple[types.VibemonTypeT, ...]
    ineffective_against: tuple[types.VibemonTypeT, ...]


class TypeMatchupSummary(FrozenSchema):
    defense: TypeDefenseSummary
    coverage: TypeCoverageSummary


class PublicVibemon(FrozenSchema):
    id: uuid.UUID
    nickname: str | None = None
    name: str
    identity: Identity
    moves: tuple[Move, ...]
    level: int
    xp: int
    evo_stage: types.EvolutionStageT
    lifecycle: types.VibemonLifecycleT
    disposition: types.VibemonDispositionT | None
    trainer_id: types.TrainerIdT | None = None
    team_slot: int | None = None
    primary_color: brand.Color | None = None
    secondary_color: brand.Color | None = None
    background_color: brand.Color | None = None
    assets: tuple[PublicAsset, ...] = ()
    candidate_review: CandidateReviewRead | None = None
    type_matchup: TypeMatchupSummary
