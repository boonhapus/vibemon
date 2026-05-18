"""Pydantic domain data objects used by the Vibemon application.

Use this module for runtime data shape, validation, serialization, and cheap
domain behavior. Keep database sessions, table declarations, and object-store
workflows in dedicated persistence or lifecycle modules.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Annotated, Any, Literal, Self, cast
import asyncio
import datetime as dt
import hashlib
import json
import math
import random
import uuid

import pydantic
import structlog

from app import brand, const, types, utils, validators
from app.balance.formulas import apply_evo_seed_bst_bias, base_stat_level_scaling
from app.data_store import monstore
from app.data_store import schema as ds_schema
from app.data_store import types as ds_types
from app.plugins.provider import VibeProvider

_LOGGER = structlog.get_logger(__name__)


# ── INTERNALS ─────────────────────────────────────────────────────────────────────────


class Schema(pydantic.BaseModel):
    """Mutable domain data object base. Use for runtime/lifecycle-shaped data."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )


class FrozenSchema(pydantic.BaseModel):
    """Immutable value object base. Use for definitions and event/log records."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        frozen=True,
    )


# ── SEED ──────────────────────────────────────────────────────────────────────────────


class BirthSnapshot(FrozenSchema):
    """Captured provider payloads used to synthesize affinities."""

    provider_payloads: dict[str, dict[str, Any]]

    async def regenerate(self, providers: Iterable[VibeProvider], seed: BirthSeed) -> Iterable[Affinity]:
        """Given a seed + captured payloads, create affinities without new API calls."""
        providers_by_name = {provider.name: provider for provider in providers}

        missing_provider_ids = [
            provider_id for provider_id in self.provider_payloads if provider_id not in providers_by_name
        ]

        if missing_provider_ids:
            missing = ", ".join(sorted(set(missing_provider_ids)))
            raise ValueError(f"Missing provider implementations for captured snapshot: {missing}")

        affinities = await asyncio.gather(
            *(
                providers_by_name[provider_id].synthesize(seed, self.provider_payloads[provider_id])
                for provider_id in sorted(self.provider_payloads)
            )
        )
        return affinities


class BirthSeed(FrozenSchema):
    """Reproducible input used to fetch provider payloads."""

    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    providers: list[VibeProvider]

    @pydantic.field_validator("timestamp")
    @classmethod
    def _normalize_to_utc(cls, v: dt.datetime) -> dt.datetime:
        """Ensure timestamp is aware UTC. SQLite strips tz, so naive values must round-trip stably."""
        if v.tzinfo is None:
            return v.replace(tzinfo=dt.UTC)
        return v.astimezone(dt.UTC)

    @property
    def datestamp(self) -> dt.date:
        """Get the date of the birth seed."""
        return self.timestamp.date()

    @staticmethod
    def _hash_seed_material(seed_material: dict[str, Any]) -> int:
        encoded = json.dumps(seed_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return int.from_bytes(hashlib.sha256(encoded).digest(), "big")

    @property
    def _rng_seed_material(self) -> dict[str, Any]:
        return {
            "geo_coords": list(self.geo_coords),
            "timestamp": self.timestamp.isoformat(timespec="microseconds"),
        }

    @property
    def rng_seed(self) -> int:
        """Stable integer seed derived from birth inputs."""
        return self._hash_seed_material(self._rng_seed_material)

    def rng_seed_for(self, namespace: str) -> int:
        """Stable integer seed for one deterministic birth subsystem."""
        return self._hash_seed_material(
            {
                "birth_seed": self._rng_seed_material,
                "namespace": namespace,
            }
        )

    def rng(self, namespace: str) -> random.Random:
        """Create a fresh deterministic RNG for one birth subsystem."""
        return random.Random(self.rng_seed_for(namespace))

    async def fetch_snapshot(self) -> BirthSnapshot:
        """Fetch provider payloads for this seed."""
        snapshots = await asyncio.gather(*(provider.fetch(self) for provider in self.providers))
        return BirthSnapshot(provider_payloads={p.name: s for p, s in zip(self.providers, snapshots, strict=True)})

    async def regenerate(self) -> Iterable[Affinity]:
        """Fetch provider payloads, then synthesize affinities from that snapshot."""
        snapshot = await self.fetch_snapshot()
        return await snapshot.regenerate(self.providers, self)


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────


class Trainer(Schema):
    """A player in the Vibemon universe."""

    id: types.TrainerIdT = pydantic.Field(default_factory=uuid.uuid7)
    username: str
    team: list[Vibemon] = pydantic.Field(default_factory=list)


class Identity(Schema):
    """Represents the core identity and battle profile of a Vibemon."""

    name: str
    """The name of the Vibemon's identity."""

    visual_notes: str | None = None
    """Supplied by the Trainer themselves."""

    provider_visual_notes: str | None = None
    """Joined provider visual descriptions captured at birth (or rerate)."""

    elements: types.IdentityElementsT

    # fmt: off
    base_hp: int         = pydantic.Field(default=70, ge= 1, le=255, json_schema_extra={"min":  1, "med": 70, "max": 255})  # noqa: E501
    base_attack: int     = pydantic.Field(default=75, ge= 5, le=190, json_schema_extra={"min":  5, "med": 75, "max": 190})  # noqa: E501
    base_defense: int    = pydantic.Field(default=70, ge= 5, le=230, json_schema_extra={"min":  5, "med": 70, "max": 230})  # noqa: E501
    base_sp_attack: int  = pydantic.Field(default=70, ge=10, le=194, json_schema_extra={"min": 10, "med": 70, "max": 194})  # noqa: E501
    base_sp_defense: int = pydantic.Field(default=70, ge=20, le=230, json_schema_extra={"min": 20, "med": 70, "max": 230})  # noqa: E501
    base_speed: int      = pydantic.Field(default=70, ge= 5, le=200, json_schema_extra={"min":  5, "med": 70, "max": 200})  # noqa: E501
    # fmt: on

    evo_seed: types.EvolutionStageT = types.EvolutionStageT.BASE
    """The max evolution stage for this Vibemon."""

    is_radiant: bool = False
    """A rare, alternative style that differs from its peer identities' appearance."""

    generation: int = 0
    """Monotonic counter bumped on balance/rebalance deploys; identifies stale identities."""

    generated_at: dt.datetime = pydantic.Field(default_factory=lambda: dt.datetime.now(tz=dt.UTC))
    """Wall-clock timestamp of this identity's most recent merge."""

    @classmethod
    def _stat_info(cls, name: types.BaseStatNameT, type: Literal["min", "med", "max"] = "med") -> int | None:
        """Fetch the descriptive statistic of the base stat field."""
        if (field := cls.model_fields.get(f"base_{name}")) and field.json_schema_extra:
            assert isinstance(field.json_schema_extra, dict), "json_schema_extra must be a dict."
            return cast(int, field.json_schema_extra[type])
        return None

    @property
    def bst(self) -> int:
        """The Base Stat Total (BST).

        Calculates the sum of all six base stats to provide a single value
        representing the species' overall power tier.
        """
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
        """Determines the tier classification based on BST ranges."""
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
        """Classify using competitive-tier stat thresholds."""
        hp = self.base_hp
        atk = self.base_attack
        sp_atk = self.base_sp_attack
        defense = self.base_defense
        sp_def = self.base_sp_defense
        speed = self.base_speed

        # Effective HP — durability that accounts for HP, not just defenses
        phys_ehp = hp * defense
        spec_ehp = hp * sp_def
        avg_ehp = (phys_ehp + spec_ehp) / 2

        best_offense = max(atk, sp_atk)

        # Speed tiers calibrated to OU-ish play
        is_very_fast = speed >= 110
        is_fast = speed >= 95
        is_slow = speed < 65

        # Offense tiers
        is_elite_off = best_offense >= 120
        is_strong_off = best_offense >= 100
        is_decent_off = best_offense >= 95

        # Bulk profiles
        is_phys_wall = phys_ehp >= 8000
        is_spec_wall = spec_ehp >= 8000
        is_any_wall = is_phys_wall or is_spec_wall
        is_mixed_bulk = phys_ehp >= 6000 and spec_ehp >= 6000
        is_frail = avg_ehp < 5000

        match True:
            # Offensive (most specific first)
            case _ if is_fast and is_strong_off and is_frail:
                return types.BattleRole.OFFENSIVE_GLASS_CANNON
            case _ if is_slow and is_elite_off:
                return types.BattleRole.OFFENSIVE_WALLBREAKER
            case _ if is_fast and is_strong_off:
                return types.BattleRole.OFFENSIVE_SWEEPER
            case _ if is_very_fast and is_decent_off:
                return types.BattleRole.OFFENSIVE_REVENGE_KILLER

            # Defensive
            case _ if is_mixed_bulk and is_decent_off:
                return types.BattleRole.DEFENSIVE_TANK
            case _ if is_any_wall and not is_decent_off:
                return types.BattleRole.DEFENSIVE_WALL
            case _ if is_mixed_bulk and is_slow:
                return types.BattleRole.DEFENSIVE_STALLER

            # Utility
            case _ if is_fast and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_PIVOT
            case _ if best_offense < 80 and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_CLERIC
            case _:
                return types.BattleRole.UTILITY


class Affinity(FrozenSchema):
    """A provider's translation of raw data into Vibemon-shaped attributes.

    Transient runtime object: produced by ``VibeProvider.synthesize`` and
    consumed by ``Affinity.merge`` to produce a ``BirthOutcome``. Not persisted.
    """

    identity: Identity
    """Represents the core, immutable personality of a Vibemon."""

    visual_notes: str | None = None
    """Supplied by a data provider."""

    intensity: float = 0.5
    """The mangitude of the steering relative to other providers."""

    provider_id: str
    """The source of steering."""

    moves: tuple[Move, ...]

    @pydantic.field_validator("moves", mode="before")
    @classmethod
    def _coerce_moves_tuple(cls, value: Any) -> Any:
        """Providers may supply a list; the schema boundary stores a tuple snapshot."""
        if isinstance(value, list):
            return tuple(value)
        return value

    @pydantic.field_validator("intensity")
    @classmethod
    def _clamp_intensity(cls, v: float) -> float:
        """Warn and clamp intensity to [0.0, 1.0] instead of failing."""
        if 0.0 <= v <= 1.0:
            return v

        clamped = utils.clamp(v, minimum=0.0, maximum=1.0)

        _LOGGER.warning(
            "Affinity.intensity out of bounds",
            original=v,
            clamp_to=clamped,
        )

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
        """Merge per-provider affinities into a Vibemon's seed state."""
        stat_keys = (
            "base_hp",
            "base_attack",
            "base_defense",
            "base_sp_attack",
            "base_sp_defense",
            "base_speed",
        )

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

        return BirthOutcome(
            identity=identity,
            moves=tuple(moves),
            evo_stage=evo_stage,
        )


class BirthOutcome(FrozenSchema):
    """Merged result of one or more provider affinities. Direct input to ``Vibemon.birth``."""

    identity: Identity
    moves: tuple[Move, ...]
    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE


class Aesthetic(Schema):
    """The visual and aural DNA of a Vibemon based on its attributes."""

    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color
    assets: dict[ds_types.AssetKind, ds_schema.AssetRef] = pydantic.Field(default_factory=dict)
    """Stable refs for blobs persisted in the monstore."""

    def has(self, kind: ds_types.AssetKind) -> bool:
        """Whether a stored ref exists for the given asset kind."""
        return kind in self.assets

    async def url_for(
        self,
        kind: ds_types.AssetKind,
        *,
        expires_in: dt.timedelta = dt.timedelta(hours=1),
    ) -> str | None:
        """Return a fetchable URL for an asset, or ``None`` if no ref exists."""
        ref = self.assets.get(kind)
        if ref is None:
            return None
        return await monstore.url(ref.key, expires_in=expires_in)

    async def bytes_for(self, kind: ds_types.AssetKind) -> bytes | None:
        """Return the raw asset bytes, or ``None`` if no ref exists."""
        ref = self.assets.get(kind)
        if ref is None:
            return None
        return await monstore.get(ref.key)

    @classmethod
    def from_vibemon(cls, vibemon: Vibemon) -> Self:
        """Derive colors from a Vibemon's elements; no assets, no I/O."""
        return cls(
            primary_color=brand.TYPE_COLORS[vibemon.elements[0]],
            secondary_color=brand.TYPE_COLORS[vibemon.elements[1]] if len(vibemon.elements) == 2 else None,
            background_color=brand.solve_background_color(
                *brand.sprite_foreground_colors(vibemon.elements),
                hue_protected=[brand.TYPE_COLORS[e] for e in vibemon.elements],
            ),
        )


class PublicAsset(FrozenSchema):
    """Fetchable asset metadata for read models."""

    kind: ds_types.AssetKind
    url: str
    content_type: str
    byte_size: int
    sha256: str


class CandidateReviewRead(FrozenSchema):
    """Trainer-visible candidate review state."""

    id: uuid.UUID
    trainer_id: types.TrainerIdT
    status: types.CandidateReviewStatusT
    shown_at: dt.datetime
    timeout_at: dt.datetime
    resolved_at: dt.datetime | None = None
    resolution: types.CandidateReviewStatusT | None = None


class PublicVibemon(FrozenSchema):
    """Frontend-ready Vibemon view with stable identity and fetchable assets."""

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


# ── MOVES ─────────────────────────────────────────────────────────────────────────────


type EffectTarget = Literal["self", "target", "all_targets", "side", "opposing_side"]


class StatusInflict(FrozenSchema):
    """Inflict a major status condition."""

    kind: Literal["status"] = "status"
    target: EffectTarget = "target"
    status: types.StatusConditionT


class StatChange(FrozenSchema):
    """Apply stat stage changes."""

    kind: Literal["stat"] = "stat"
    target: EffectTarget = "target"
    changes: dict[types.StatStageNameT, int]


class Drain(FrozenSchema):
    """Heal the user for a ratio of damage dealt."""

    kind: Literal["drain"] = "drain"
    ratio: float


class Recoil(FrozenSchema):
    """Damage the user for a ratio of damage dealt."""

    kind: Literal["recoil"] = "recoil"
    ratio: float


class WeatherSet(FrozenSchema):
    """Set field weather."""

    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    turns: int


class Heal(FrozenSchema):
    """Heal a target by a max HP ratio."""

    kind: Literal["heal"] = "heal"
    target: EffectTarget = "self"
    ratio: float


type Effect = Annotated[
    StatusInflict | StatChange | Drain | Recoil | WeatherSet | Heal,
    pydantic.Discriminator("kind"),
]


class EffectGroup(FrozenSchema):
    """A shared-chance group of effects."""

    chance: float = 1.0
    trigger: Literal["on_hit", "on_use", "after_damage"] = "on_hit"
    effects: tuple[Effect, ...] = ()


class ConditionalOverride(FrozenSchema):
    """Declarative override for conditional move behavior."""

    valid: bool | None = None
    priority_delta: int = 0
    accuracy_override: float | None = None
    power_multiplier: float | None = None
    flavor_key: str | None = None


class IfOpponentAttacking(FrozenSchema):
    """Condition matching an opponent's attacking action."""

    kind: Literal["opponent_attacking"] = "opponent_attacking"
    on_match: ConditionalOverride
    on_miss: ConditionalOverride | None = None


class IfWeather(FrozenSchema):
    """Condition matching current field weather."""

    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    on_match: ConditionalOverride


class IfHpBelow(FrozenSchema):
    """Condition matching user HP ratio."""

    kind: Literal["hp_below"] = "hp_below"
    threshold: float
    on_match: ConditionalOverride


class RandomPower(FrozenSchema):
    """Condition selecting a random power bucket."""

    kind: Literal["random_power"] = "random_power"
    buckets: tuple[tuple[float, int], ...]


type Condition = Annotated[
    IfOpponentAttacking | IfWeather | IfHpBelow | RandomPower,
    pydantic.Discriminator("kind"),
]


class MoveBehavior(FrozenSchema):
    """First-party move behavior references and declarative conditions."""

    conditions: tuple[Condition, ...] = ()
    script_id: str | None = None


class Move(FrozenSchema):
    """A move that a Vibemon can learn and use in battle."""

    name: str
    """The move's name."""

    flavor_text: str
    """The move's description, may include visual notes."""

    type: types.VibemonTypeT
    category: types.MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0  # NULL = Gauranteed hit.
    pp: int = 10
    priority: Annotated[int, validators.ensure_between_abs_7] = 0
    effects: tuple[EffectGroup, ...] = ()
    behavior: MoveBehavior = pydantic.Field(default_factory=MoveBehavior)
    target: types.MoveTargetT = types.MoveTargetT.SINGLE
    level_requirement: int = 1

    def __hash__(self) -> int:
        """There should be no two moves named the same."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """There should be no two moves named the same."""
        if not isinstance(other, Move):
            return NotImplemented
        return self.name == other.name


# ── PERSONALITY ───────────────────────────────────────────────────────────────────────


class Vibemon(Schema):
    """Innate properties of a Vibemon with derived actual stats."""

    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid7)
    """Stable identifier; persists 1:1 with the DB row and asset key prefix."""

    nickname: str | None = None
    """The name given to the Vibemon by the Trainer."""

    identity: Identity
    """Merged identity carrying species-level stats and notes. 1:1 with the Vibemon row."""

    moves: tuple[Move, ...] = ()
    """The Vibemon's active 4 moves (or fewer at low levels)."""

    level: int = 1
    """The Vibemon's current level."""

    xp: int = 0
    """Cumulative experience points; canonical progression. ``level`` is the cached read."""

    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE
    """Current evolution stage; advances on evolution events. Capped at ``identity.evo_seed``."""

    trainer_id: types.TrainerIdT | None = None
    """Trainer ownership. ``None`` means wild; populated means owned."""

    team_slot: int | None = None
    """Active party slot (0..5) when on a trainer's team; ``None`` when in storage."""

    lifecycle: types.VibemonLifecycleT = types.VibemonLifecycleT.BORN
    """Asset realization state. Mutated only by ``app.lifecycle`` functions."""

    aesthetic: Aesthetic | None = None
    """Visual and aural identity, including stored asset refs."""

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
        """Pure factory: merge raw affinities. No network. Name + assets deferred."""
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
        """Re-run merge/balance with stored identity preserved. No network."""
        instance = cls.birth(
            *affinities,
            birth_seed=birth_seed,
            nickname=nickname,
            core_identity=core_identity,
        )
        instance.id = id
        instance.identity = instance.identity.model_copy(update={"name": name})
        instance.level = level
        instance.xp = xp
        if evo_stage is not None:
            instance.evo_stage = evo_stage
        instance.lifecycle = types.VibemonLifecycleT.BORN
        # Refresh aesthetic to drop old asset refs; rebirth has no network so
        # it cannot regenerate blobs. Callers must rechristen for new assets.
        instance.aesthetic = Aesthetic.from_vibemon(instance)
        return instance

    async def lineage(self, snapshot: BirthSnapshot, seed: BirthSeed) -> list[Affinity]:
        """Rebuild the per-provider affinities that contributed to this Vibemon.

        Cold-path operation: re-runs each provider's ``synthesize`` against the
        cached snapshot payloads. No network. Use for lineage UI and rerate.
        """
        return list(await snapshot.regenerate(seed.providers, seed))

    @property
    def name(self) -> str:
        """The nickname or identity name of a Vibemon."""
        return self.nickname or self.identity.name

    @property
    def elements(self) -> tuple[types.VibemonTypeT, ...]:
        """The Vibemon's elemental typing."""
        return self.identity.elements

    @property
    def is_wild(self) -> bool:
        """A wild Vibemon has no trainer."""
        return self.trainer_id is None

    @property
    def is_owned(self) -> bool:
        """An owned Vibemon has a trainer."""
        return self.trainer_id is not None

    @property
    def hp(self) -> int:
        """
        Calculates the actual HP stat.

        HP adds level scaling for extra survivability at higher levels.
        """
        return base_stat_level_scaling(self.identity.base_hp, level=self.level, true_floor=10) + self.level  # fmt: skip

    @property
    def attack(self) -> int:
        """Calculates the actual Attack stat."""
        return base_stat_level_scaling(self.identity.base_attack, level=self.level)

    @property
    def defense(self) -> int:
        """Calculates the actual Defense stat."""
        return base_stat_level_scaling(self.identity.base_defense, level=self.level)

    @property
    def sp_attack(self) -> int:
        """Calculates the actual Special Attack stat."""
        return base_stat_level_scaling(self.identity.base_sp_attack, level=self.level)

    @property
    def sp_defense(self) -> int:
        """Calculates the actual Special Defense stat."""
        return base_stat_level_scaling(self.identity.base_sp_defense, level=self.level)

    @property
    def speed(self) -> int:
        """Calculates the actual Speed stat."""
        return base_stat_level_scaling(self.identity.base_speed, level=self.level)
