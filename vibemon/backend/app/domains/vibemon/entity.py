"""Vibemon runtime-domain schemas."""

from typing import Any, Self
import uuid

import pydantic

from app.core.ids import TrainerIdT
from app.core.schema import Schema
from app.domains.generation import affinity as generation_affinity
from app.domains.generation.birth import birth_outcome_from_affinities
from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.sprite import types as sprite_types
from app.domains.vibemon import brand, types
from app.domains.vibemon import identity as vibemon_identity
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.domains.vibemon.progression.types import GrowthGroupT
from app.domains.vibemon.strength_formulas import base_stat_level_scaling

__all__ = ["Aesthetic", "Vibemon"]


class Aesthetic(Schema):
    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color
    assets: dict[AssetKind, AssetRef] = pydantic.Field(default_factory=dict)

    def has(self, kind: AssetKind) -> bool:
        return kind in self.assets

    @classmethod
    def from_vibemon(cls, vibemon: Vibemon) -> Self:
        return cls(
            primary_color=brand.TYPE_COLORS[vibemon.elements[0]],
            secondary_color=brand.TYPE_COLORS[vibemon.elements[1]] if len(vibemon.elements) == 2 else None,
            background_color=brand.solve_background_color(
                *brand.sprite_foreground_colors(vibemon.elements),
                hue_protected=[brand.TYPE_COLORS[e] for e in vibemon.elements],
            ),
        )


class Vibemon(Schema):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid7)
    nickname: str | None = None
    identity: vibemon_identity.Identity
    moves: tuple[Move, ...] = ()
    level: int = 1
    xp: int = 0
    growth_rate: GrowthGroupT = GrowthGroupT.MEDIUM
    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE
    trainer_id: TrainerIdT | None = None
    crew_slot: int | None = None
    lifecycle: types.VibemonLifecycleT = types.VibemonLifecycleT.BORN
    aesthetic: Aesthetic | None = None
    reference_detected_facing: sprite_types.SpriteFacing | None = None

    @pydantic.field_validator("moves", mode="before")
    @classmethod
    def _coerce_moves_tuple(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @pydantic.field_validator("moves")
    @classmethod
    def _validate_moves_count(cls, value: tuple[Move, ...]) -> tuple[Move, ...]:
        if len(value) > 4:
            raise ValueError(f"Vibemon cannot have more than 4 active moves, got {len(value)}")
        return value

    @classmethod
    def birth(
        cls,
        *affinities: generation_affinity.Affinity,
        birth_seed: BirthSeed,
        nickname: str | None = None,
    ) -> Self:
        outcome = birth_outcome_from_affinities(*affinities, birth_seed=birth_seed)
        instance = cls(
            nickname=nickname,
            identity=outcome.identity,
            moves=outcome.moves,
            level=1,
            growth_rate=outcome.growth_rate,
            evo_stage=outcome.evo_stage,
        )
        instance.aesthetic = Aesthetic.from_vibemon(instance)
        return instance

    async def lineage(self, snapshot: BirthSnapshot, seed: BirthSeed) -> list[generation_affinity.Affinity]:
        return list(await snapshot.regenerate(seed.providers, seed))

    @property
    def name(self) -> str:
        return self.nickname or self.identity.name

    @property
    def elements(self) -> tuple[types.VibemonTypeT, ...]:
        return self.identity.elements

    @property
    def is_wild(self) -> bool:
        return self.trainer_id is None

    @property
    def is_owned(self) -> bool:
        return self.trainer_id is not None

    @property
    def hp(self) -> int:
        return base_stat_level_scaling(self.identity.base.hp, level=self.level, true_floor=10) + self.level

    @property
    def attack(self) -> int:
        return base_stat_level_scaling(self.identity.base.attack, level=self.level)

    @property
    def defense(self) -> int:
        return base_stat_level_scaling(self.identity.base.defense, level=self.level)

    @property
    def sp_attack(self) -> int:
        return base_stat_level_scaling(self.identity.base.sp_attack, level=self.level)

    @property
    def sp_defense(self) -> int:
        return base_stat_level_scaling(self.identity.base.sp_defense, level=self.level)

    @property
    def speed(self) -> int:
        return base_stat_level_scaling(self.identity.base.speed, level=self.level)
