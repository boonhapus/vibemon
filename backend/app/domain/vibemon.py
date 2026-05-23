"""Vibemon identity and runtime-domain schemas."""

from __future__ import annotations

from typing import Any, Literal, Self, cast
import datetime as dt
import math
import random
import uuid

import pydantic
import structlog

from app import brand, const, types, utils
from app.balance.formulas import apply_evo_seed_bst_bias, base_stat_level_scaling
from app.data_store import monstore
from app.data_store import schema as ds_schema
from app.data_store import types as ds_types
from app.domain.birth import BirthSeed, BirthSnapshot, FrozenSchema, Schema
from app.domain.move import Move

_LOGGER = structlog.get_logger(__name__)


class Trainer(Schema):
    id: types.TrainerIdT = pydantic.Field(default_factory=uuid.uuid7)
    username: str
    team: list[Vibemon] = pydantic.Field(default_factory=list)


class Identity(Schema):
    name: str
    visual_notes: str | None = None
    provider_visual_notes: str | None = None
    elements: types.IdentityElementsT

    base_hp: int = pydantic.Field(default=70, ge=1, le=255, json_schema_extra={"min": 1, "med": 70, "max": 255})
    base_attack: int = pydantic.Field(default=75, ge=5, le=190, json_schema_extra={"min": 5, "med": 75, "max": 190})
    base_defense: int = pydantic.Field(default=70, ge=5, le=230, json_schema_extra={"min": 5, "med": 70, "max": 230})
    base_sp_attack: int = pydantic.Field(
        default=70,
        ge=10,
        le=194,
        json_schema_extra={"min": 10, "med": 70, "max": 194},
    )
    base_sp_defense: int = pydantic.Field(
        default=70,
        ge=20,
        le=230,
        json_schema_extra={"min": 20, "med": 70, "max": 230},
    )
    base_speed: int = pydantic.Field(default=70, ge=5, le=200, json_schema_extra={"min": 5, "med": 70, "max": 200})

    evo_seed: types.EvolutionStageT = types.EvolutionStageT.BASE
    is_radiant: bool = False
    generation: int = 0
    generated_at: dt.datetime = pydantic.Field(default_factory=lambda: dt.datetime.now(tz=dt.UTC))

    @classmethod
    def _stat_info(cls, name: types.BaseStatNameT, type: Literal["min", "med", "max"] = "med") -> int | None:
        if (field := cls.model_fields.get(f"base_{name}")) and field.json_schema_extra:
            assert isinstance(field.json_schema_extra, dict), "json_schema_extra must be a dict."
            return cast(int, field.json_schema_extra[type])
        return None

    @property
    def bst(self) -> int:
        return (
            self.base_hp
            + self.base_attack
            + self.base_defense
            + self.base_sp_attack
            + self.base_sp_defense
            + self.base_speed
        )

    @property
    def tier(self) -> types.TierT:
        match self.bst:
            case b if b < 400:
                return types.TierT.RUNT
            case b if b < 500:
                return types.TierT.MID
            case b if b < 570:
                return types.TierT.SOLID
            case b if b < 670:
                return types.TierT.APEX
            case _:
                return types.TierT.MYTHIC

    @property
    def battle_role(self) -> types.BattleRole:
        hp = self.base_hp
        atk = self.base_attack
        sp_atk = self.base_sp_attack
        defense = self.base_defense
        sp_def = self.base_sp_defense
        speed = self.base_speed

        phys_ehp = hp * defense
        spec_ehp = hp * sp_def
        avg_ehp = (phys_ehp + spec_ehp) / 2
        best_offense = max(atk, sp_atk)

        is_very_fast = speed >= 110
        is_fast = speed >= 95
        is_slow = speed < 65

        is_elite_off = best_offense >= 120
        is_strong_off = best_offense >= 100
        is_decent_off = best_offense >= 95

        is_phys_wall = phys_ehp >= 8000
        is_spec_wall = spec_ehp >= 8000
        is_any_wall = is_phys_wall or is_spec_wall
        is_mixed_bulk = phys_ehp >= 6000 and spec_ehp >= 6000
        is_frail = avg_ehp < 5000

        match True:
            case _ if is_fast and is_strong_off and is_frail:
                return types.BattleRole.OFFENSIVE_GLASS_CANNON
            case _ if is_slow and is_elite_off:
                return types.BattleRole.OFFENSIVE_WALLBREAKER
            case _ if is_fast and is_strong_off:
                return types.BattleRole.OFFENSIVE_SWEEPER
            case _ if is_very_fast and is_decent_off:
                return types.BattleRole.OFFENSIVE_REVENGE_KILLER
            case _ if is_mixed_bulk and is_decent_off:
                return types.BattleRole.DEFENSIVE_TANK
            case _ if is_any_wall and not is_decent_off:
                return types.BattleRole.DEFENSIVE_WALL
            case _ if is_mixed_bulk and is_slow:
                return types.BattleRole.DEFENSIVE_STALLER
            case _ if is_fast and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_PIVOT
            case _ if best_offense < 80 and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_CLERIC
            case _:
                return types.BattleRole.UTILITY


class Affinity(FrozenSchema):
    identity: Identity
    visual_notes: str | None = None
    intensity: float = 0.5
    provider_id: str
    moves: tuple[Move, ...]

    @pydantic.field_validator("moves", mode="before")
    @classmethod
    def _coerce_moves_tuple(cls, value: Any) -> Any:
        if isinstance(value, list):
            return tuple(value)
        return value

    @pydantic.field_validator("intensity")
    @classmethod
    def _clamp_intensity(cls, v: float) -> float:
        if 0.0 <= v <= 1.0:
            return v
        clamped = utils.clamp(v, minimum=0.0, maximum=1.0)
        _LOGGER.warning("Affinity.intensity out of bounds", original=v, clamp_to=clamped)
        return clamped

    @classmethod
    def merge(
        cls,
        *affinities: Affinity,
        core_identity_description: str | None = None,
        rng: random.Random | None = None,
        evo_rng: random.Random | None = None,
        radiant_rng: random.Random | None = None,
    ) -> BirthOutcome:
        stat_keys = ("base_hp", "base_attack", "base_defense", "base_sp_attack", "base_sp_defense", "base_speed")
        if rng is None:
            rng = random.Random()
        if evo_rng is None:
            evo_rng = rng
        if radiant_rng is None:
            radiant_rng = rng

        name = ""
        total = 0
        stats = {k: 0 for k in stat_keys}
        notes: list[str] = []
        pop_e: list[tuple[types.VibemonTypeT, int]] = []
        pop_m: list[tuple[Move, int]] = []

        for idx, affinity in enumerate(sorted(affinities, key=lambda a: (-a.intensity, a.provider_id))):
            weight = int(affinity.intensity * 100)
            total += weight
            for k in stat_keys:
                stats[k] += weight * math.floor(getattr(affinity.identity, k))
            pop_e.extend((e, weight) for e in affinity.identity.elements)
            pop_m.extend((m, weight) for m in affinity.moves)
            if idx == 0:
                name = affinity.identity.name
            if affinity.visual_notes:
                notes.append(f"{affinity.visual_notes} ({weight}%)")

        try:
            stats_merged = {k: math.floor(stats[k] / total) for k in stat_keys}
            elements = utils.weighted_sample(*zip(*pop_e, strict=True), k=rng.randint(1, min(2, len(pop_e))), rng=rng)
            moves = utils.weighted_sample(*zip(*pop_m, strict=True), k=rng.randint(2, min(3, len(pop_m))), rng=rng)
        except ZeroDivisionError:
            _LOGGER.exception("Total is zero.", affinities=affinities)
            raise

        evo_seed = types.EvolutionStageT.random_seed(rng=evo_rng)
        evo_stage = types.EvolutionStageT.BASE
        stats_scaled = apply_evo_seed_bst_bias(stats_merged, evo_seed=evo_seed, evo_stage=evo_stage)

        identity = Identity(
            name=name,
            visual_notes=core_identity_description,
            provider_visual_notes=" ".join(notes) or None,
            elements=tuple(dict.fromkeys(elements)),
            evo_seed=evo_seed,
            is_radiant=radiant_rng.randint(1, const.RADIANT_ODDS) == const.RADIANT_ODDS,
            **stats_scaled,
        )

        return BirthOutcome(identity=identity, moves=tuple(moves), evo_stage=evo_stage)


class BirthOutcome(FrozenSchema):
    identity: Identity
    moves: tuple[Move, ...]
    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE


class Aesthetic(Schema):
    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color
    assets: dict[ds_types.AssetKind, ds_schema.AssetRef] = pydantic.Field(default_factory=dict)

    def has(self, kind: ds_types.AssetKind) -> bool:
        return kind in self.assets

    async def url_for(
        self,
        kind: ds_types.AssetKind,
        *,
        expires_in: dt.timedelta = dt.timedelta(hours=1),
    ) -> str | None:
        ref = self.assets.get(kind)
        if ref is None:
            return None
        return await monstore.url(ref.key, expires_in=expires_in)

    async def bytes_for(self, kind: ds_types.AssetKind) -> bytes | None:
        ref = self.assets.get(kind)
        if ref is None:
            return None
        return await monstore.get(ref.key)

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
    identity: Identity
    moves: tuple[Move, ...] = ()
    level: int = 1
    xp: int = 0
    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE
    trainer_id: types.TrainerIdT | None = None
    team_slot: int | None = None
    lifecycle: types.VibemonLifecycleT = types.VibemonLifecycleT.BORN
    aesthetic: Aesthetic | None = None

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
        *affinities: Affinity,
        birth_seed: BirthSeed,
        nickname: str | None = None,
        core_identity: str | None = None,
    ) -> Self:
        if not affinities:
            raise ValueError("Vibemon must be born from at least one Affinity!")
        outcome = Affinity.merge(
            *affinities,
            core_identity_description=core_identity,
            rng=birth_seed.rng("affinity.merge"),
            evo_rng=birth_seed.rng("identity.evo_seed"),
            radiant_rng=birth_seed.rng("identity.radiant"),
        )
        instance = cls(
            nickname=nickname,
            identity=outcome.identity,
            moves=outcome.moves,
            level=1,
            evo_stage=outcome.evo_stage,
        )
        instance.aesthetic = Aesthetic.from_vibemon(instance)
        return instance

    @classmethod
    def rebirth(
        cls,
        *affinities: Affinity,
        id: uuid.UUID,
        name: str,
        birth_seed: BirthSeed,
        core_identity: str | None = None,
        nickname: str | None = None,
        level: int = 1,
        xp: int = 0,
        evo_stage: types.EvolutionStageT | None = None,
    ) -> Self:
        instance = cls.birth(*affinities, birth_seed=birth_seed, nickname=nickname, core_identity=core_identity)
        instance.id = id
        instance.identity = instance.identity.model_copy(update={"name": name})
        instance.level = level
        instance.xp = xp
        if evo_stage is not None:
            instance.evo_stage = evo_stage
        instance.lifecycle = types.VibemonLifecycleT.BORN
        instance.aesthetic = Aesthetic.from_vibemon(instance)
        return instance

    async def lineage(self, snapshot: BirthSnapshot, seed: BirthSeed) -> list[Affinity]:
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
        return base_stat_level_scaling(self.identity.base_hp, level=self.level, true_floor=10) + self.level

    @property
    def attack(self) -> int:
        return base_stat_level_scaling(self.identity.base_attack, level=self.level)

    @property
    def defense(self) -> int:
        return base_stat_level_scaling(self.identity.base_defense, level=self.level)

    @property
    def sp_attack(self) -> int:
        return base_stat_level_scaling(self.identity.base_sp_attack, level=self.level)

    @property
    def sp_defense(self) -> int:
        return base_stat_level_scaling(self.identity.base_sp_defense, level=self.level)

    @property
    def speed(self) -> int:
        return base_stat_level_scaling(self.identity.base_speed, level=self.level)
