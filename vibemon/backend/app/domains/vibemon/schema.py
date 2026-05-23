"""Public Vibemon read-model schemas."""

from __future__ import annotations

import uuid

from app.core.ids import TrainerIdT
from app.core.schema import FrozenSchema
from app.domains.adoption.schema import CandidateReviewRead
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon import brand
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT


class PublicAsset(FrozenSchema):
    kind: AssetKind
    url: str
    content_type: str
    byte_size: int
    sha256: str


class TypeDefenseSummary(FrozenSchema):
    weak_to: tuple[VibemonTypeT, ...]
    resists: tuple[VibemonTypeT, ...]
    immune_to: tuple[VibemonTypeT, ...]


class TypeCoverageSummary(FrozenSchema):
    move_types: tuple[VibemonTypeT, ...]
    strong_against: tuple[VibemonTypeT, ...]
    ineffective_against: tuple[VibemonTypeT, ...]


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
    evo_stage: EvolutionStageT
    lifecycle: VibemonLifecycleT
    disposition: VibemonDispositionT | None
    trainer_id: TrainerIdT | None = None
    team_slot: int | None = None
    primary_color: brand.Color | None = None
    secondary_color: brand.Color | None = None
    background_color: brand.Color | None = None
    assets: tuple[PublicAsset, ...] = ()
    candidate_review: CandidateReviewRead | None = None
    type_matchup: TypeMatchupSummary
