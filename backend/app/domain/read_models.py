"""Read-model schemas exposed by service/API layers."""

from __future__ import annotations

import datetime as dt
import uuid

from app import brand, types
from app.data_store import types as ds_types
from app.domain.birth import FrozenSchema
from app.domain.move import Move
from app.domain.vibemon import Identity


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
