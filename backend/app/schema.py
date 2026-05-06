from collections.abc import Iterable
from typing import Annotated, Any, Literal, Self
import asyncio
import datetime as dt
import math
import random
import structlog

import pydantic

from app.balance.formulas import base_stat_level_scaling
from app.genai.client import generate_battle_cry, generate_vibemon_sprite
from app.plugins.provider import VibeProvider
from app.settings import settings
from app import brand, const, types, utils, validators

_LOGGER = structlog.get_logger(__name__)


# ── INTERNALS ─────────────────────────────────────────────────────────────────────────


class _Static(pydantic.BaseModel):
    """Base configuration for all models."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
    )


class _Transient(pydantic.BaseModel):
    """Base configuration for all models."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        frozen=False,
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )


# ── SEED ──────────────────────────────────────────────────────────────────────────────


class BirthContext(_Static, arbitrary_types_allowed=True):
    """Represents the context in which a Vibemon is being created under."""

    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    providers: list[VibeProvider]

    async def regenerate(self) -> Iterable[Affinity]:
        """Given the context, create the nature of a vibemon."""
        affinities = await asyncio.gather(*(p.synthesize(self) for p in self.providers))
        return affinities


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────


class Trainer(_Transient):
    """A player in the Vibemon universe."""

    id: types.TrainerIdT
    username: str
    team: list[Vibemon] = pydantic.Field(default_factory=list)


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────


class Identity(_Static):
    """Represents the core, immutable personality of a Vibemon."""

    name: str
    """The name of the Vibemon's identity."""

    visual_notes: str | None = None
    """Supplied by the Trainer themselves."""

    elements: types.IdentityElementsT
    base_hp: int = pydantic.Field(default=70, ge=1, le=255, json_schema_extra={"min": 1, "med": 70, "max": 255})
    base_attack: int = pydantic.Field(default=75, ge=5, le=190, json_schema_extra={"min": 5, "med": 75, "max": 190})
    base_defense: int = pydantic.Field(default=70, ge=5, le=230, json_schema_extra={"min": 5, "med": 70, "max": 230})
    base_sp_attack: int = pydantic.Field(
        default=70, ge=10, le=194, json_schema_extra={"min": 10, "med": 70, "max": 194}
    )
    base_sp_defense: int = pydantic.Field(
        default=70, ge=20, le=230, json_schema_extra={"min": 20, "med": 70, "max": 230}
    )
    base_speed: int = pydantic.Field(default=70, ge=5, le=200, json_schema_extra={"min": 5, "med": 70, "max": 200})

    evo_seed: int = pydantic.Field(default_factory=lambda: random.randint(1, 3))
    """The number of evolutions for this Vibemon."""

    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE
    """The current evolution of this Vibemon."""

    is_mythic: bool = pydantic.Field(default_factory=lambda: random.randint(1, const.MYTHIC_ODDS) == const.MYTHIC_ODDS)
    """A rare, alternative style that differs from its peer identities' appearance."""

    @classmethod
    def _stat_info(cls, name: types.BaseStatNameT, type: Literal["min", "med", "max"] = "med") -> int | None:
        """Fetch the descriptive statistic of the base stat field."""
        if (field := cls.model_fields.get(f"base_{name}")) and field.json_schema_extra:
            return field.json_schema_extra[type]
        return None

    @property
    def bst(self) -> int:
        """
        The Base Stat Total (BST).

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
        """
        Determines the tier classification based on BST ranges.

        RUNT .... BST   < 400
        MID ..... BST 400-499
        SOLID ... BST 500-569
        APEX .... BST 570-669
        MYTHIC .. BST  >= 670
        """
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
    def battle_role(self) -> tuple[str, str]:
        """
        Determines the battle role based on stat distribution.

        Returns a tuple of (role_name, description) classifying the Vibemon as:
        - OFFENSIVE (Sweeper, Wallbreaker, Glass Cannon, Revenge Killer)
        - DEFENSIVE (Wall, Tank, Staller)
        - UTILITY (Pivot, Entry Hazard Lead, Cleric, Screen Setter, Suicide Lead)

        Uses percentages to determine relative stat distribution.
        """
        offense_weight = self.base_attack + self.base_sp_attack + self.base_speed
        defense_weight = self.base_hp + self.base_defense + self.base_sp_defense
        speed_weight = self.base_speed

        off_pct = offense_weight / self.bst
        def_pct = defense_weight / self.bst
        spd_pct = speed_weight / self.bst
        ehp_pct = self.base_hp / self.bst

        atk = self.base_attack
        sp_atk = self.base_sp_attack
        defense = self.base_defense
        sp_def = self.base_sp_defense
        speed = self.base_speed

        is_fast = speed >= 80
        is_slow = speed < 50
        is_squishy = defense < 50 and sp_def < 50
        is_tanky = defense >= 70 or sp_def >= 70
        is_fast_breaker = is_fast and (atk >= 70 or sp_atk >= 70)
        is_slow_breaker = is_slow and (atk >= 70 or sp_atk >= 70)

        match True:
            case _ if def_pct > 0.5 and is_tanky and ehp_pct > 0.2:
                return ("DEFENSIVE_WALL", "A resilient wall with high HP and defenses designed to absorb hits.")
            case _ if def_pct > 0.4 and (atk >= 50 or sp_atk >= 50):
                return ("DEFENSIVE_TANK", "A defensive tank that can absorb hits and fight back.")
            case _ if def_pct > 0.45 and is_slow:
                return ("DEFENSIVE_STALLER", "A slow but durable staller that outlasts opponents.")
            case _ if off_pct > 0.55 and is_fast and is_squishy:
                return ("OFFENSIVE_GLASS_CANNON", "Extreme speed and power but fragile — must OHKO or faint.")
            case _ if off_pct > 0.55 and is_fast_breaker:
                return ("OFFENSIVE_SWEEPER", "Fast and powerful — designed to sweep weakened teams.")
            case _ if off_pct > 0.55 and is_slow_breaker:
                return ("OFFENSIVE_WALLBREAKER", "Slow but devastating — breaks through defensive Pokemon.")
            case _ if off_pct > 0.5 and spd_pct > 0.25:
                return ("OFFENSIVE_REVENGE_KILLER", "Fast pivot designed to pick off weakened opponents.")
            case _ if spd_pct > 0.3 and def_pct > 0.35:
                return ("UTILITY_PIVOT", "A balanced pivot that switches out to maintain momentum.")
            case _ if off_pct < 0.45 and def_pct < 0.45:
                return ("UTILITY_CLERIC", "A support-focused role that heals and clears status.")
            case _:
                return ("UTILITY", "A balanced utility role that supports the team.")


class Affinity(_Static, validate_assignment=True):
    """Represents the nature of a Vibemon, steered by the source provider.."""

    identity: Identity
    """Represents the core, immutable personality of a Vibemon."""

    visual_notes: str | None = None
    """Supplied by a data provider."""

    intensity: float = 0.5
    """The mangitude of the steering relative to other providers."""

    provider_id: str
    """The source of steering."""

    moves: list[Move]

    @pydantic.model_validator(mode="after")
    def _validate_intensity(self) -> Self:
        """Warn and clamp intensity to [0.0, 1.0] instead of failing."""
        if 0.0 <= self.intensity <= 1.0:
            return self

        old = float(self.intensity)

        self.intensity = utils.clamp(old, minimum=0.0, maximum=1.0)

        _LOGGER.warning(
            "Affinity.intensity out of bounds",
            provider=self.provider_id,
            original=old,
            clamp_to=self.intensity,
        )

        return self

    @classmethod
    def merge(cls, *affinities: Affinity, core_identity_description: str | None = None) -> Affinity:
        """Create an Affinity by merging a number of affinities."""
        stat_keys = (
            "base_hp",
            "base_attack",
            "base_defense",
            "base_sp_attack",
            "base_sp_defense",
            "base_speed",
        )

        name = ""
        total = 0
        stats = {k: 0 for k in stat_keys}
        notes = []
        pop_e: list[tuple[types.VibemonTypeT, int]] = []
        pop_m: list[tuple[Move, int]] = []

        for idx, affinity in enumerate(sorted(affinities, key=lambda a: a.intensity, reverse=True)):
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
            elements = utils.weighted_sample(*zip(*pop_e), k=random.randint(1, min(2, len(pop_e))))
            moves = utils.weighted_sample(*zip(*pop_m), k=random.randint(2, min(3, len(pop_m))))
        except ZeroDivisionError:
            _LOGGER.exception("Total is zero.", affinities=affinities)
            raise

        merged_affinity = Affinity(
            identity=Identity(
                name=name,
                visual_notes=core_identity_description,
                elements=tuple(set(elements)),
                **stats_merged,
            ),
            visual_notes=" ".join(notes),
            provider_id="merged",
            intensity=1,
            moves=moves,
        )

        return merged_affinity


class Aesthetic(_Transient):
    """The visual and aural DNA of a Vibemon based on its attributes."""

    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color

    # ── LOCKED BEHIND ASYNC GENERATION ────────────────────────────────────────────────

    sprites: types.SpriteLayout | None = None
    """All sprites that represent the vibemon."""

    battle_cry: bytes | None = None
    """All sounds that the Vibemon makes."""

    # ── LOCKED BEHIND ASYNC GENERATION ────────────────────────────────────────────────

    _vibemon: Vibemon | None = None

    @pydantic.field_validator("sprites", mode="before")
    def _unwrap_sprite_sheet(cls, value: bytes | types.SpriteLayout | None) -> types.SpriteLayout | None:
        if isinstance(value, bytes):
            value = utils.extract_sprites(image=value)

        return value

    async def regenerate(self) -> Self:
        """ """
        if self._vibemon is None:
            raise ValueError("No base Vibemon to regenerate from.")

        tasks: list[asyncio.Task] = []

        async with asyncio.TaskGroup() as g:
            t = g.create_task(generate_vibemon_sprite(vibemon=self._vibemon))
            t.set_name("sprites")
            tasks.append(t)

            t = asyncio.create_task(generate_battle_cry(vibemon=self._vibemon))
            t.set_name("battle_cry")
            tasks.append(t)

        for task in tasks:
            setattr(self, task.get_name(), task.result())

        return self

    @classmethod
    def from_vibemon(cls, vibemon: Vibemon) -> Self:
        """Generalize from the Vibemon's attributes."""
        data = {
            "primary_color": brand.TYPE_COLORS[vibemon.elements[0]],
            "secondary_color": brand.TYPE_COLORS[vibemon.elements[1]] if len(vibemon.elements) == 2 else None,
            "background_color": brand.solve_background_color(*(brand.TYPE_COLORS[e] for e in vibemon.elements)),
        }

        ins = cls(**data)
        ins._vibemon = vibemon
        return ins


# ── MOVES ─────────────────────────────────────────────────────────────────────────────


class MoveEffect(_Static):
    """Secondary effects that may occur when a move is used."""

    status_inflict: types.StatusConditionT | None = None
    stat_changes: dict[types.StatStageNameT, int] = pydantic.Field(default_factory=dict)
    target_self: bool = False
    chance: float = 1.0


type EffectTarget = Literal["self", "target", "all_targets", "side", "opposing_side"]


class StatusInflict(_Static):
    """Inflict a major status condition."""

    kind: Literal["status"] = "status"
    target: EffectTarget = "target"
    status: types.StatusConditionT


class StatChange(_Static):
    """Apply stat stage changes."""

    kind: Literal["stat"] = "stat"
    target: EffectTarget = "target"
    changes: dict[types.StatStageNameT, int]


class Drain(_Static):
    """Heal the user for a ratio of damage dealt."""

    kind: Literal["drain"] = "drain"
    ratio: float


class Recoil(_Static):
    """Damage the user for a ratio of damage dealt."""

    kind: Literal["recoil"] = "recoil"
    ratio: float


class WeatherSet(_Static):
    """Set field weather."""

    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    turns: int


class Heal(_Static):
    """Heal a target by a max HP ratio."""

    kind: Literal["heal"] = "heal"
    target: EffectTarget = "self"
    ratio: float


type Effect = Annotated[
    StatusInflict | StatChange | Drain | Recoil | WeatherSet | Heal,
    pydantic.Discriminator("kind"),
]


class EffectGroup(_Static):
    """A shared-chance group of effects."""

    chance: float = 1.0
    trigger: Literal["on_hit", "on_use", "after_damage"] = "on_hit"
    effects: tuple[Effect, ...] = ()


class ConditionalOverride(_Static):
    """Declarative override for conditional move behavior."""

    valid: bool | None = None
    priority_delta: int = 0
    accuracy_override: float | None = None
    power_multiplier: float | None = None
    flavor_key: str | None = None


class IfOpponentAttacking(_Static):
    """Condition matching an opponent's attacking action."""

    kind: Literal["opponent_attacking"] = "opponent_attacking"
    on_match: ConditionalOverride
    on_miss: ConditionalOverride | None = None


class IfWeather(_Static):
    """Condition matching current field weather."""

    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    on_match: ConditionalOverride


class IfHpBelow(_Static):
    """Condition matching user HP ratio."""

    kind: Literal["hp_below"] = "hp_below"
    threshold: float
    on_match: ConditionalOverride


class RandomPower(_Static):
    """Condition selecting a random power bucket."""

    kind: Literal["random_power"] = "random_power"
    buckets: tuple[tuple[float, int], ...]


type Condition = Annotated[
    IfOpponentAttacking | IfWeather | IfHpBelow | RandomPower,
    pydantic.Discriminator("kind"),
]


class MoveBehavior(_Static):
    """First-party move behavior references and declarative conditions."""

    conditions: tuple[Condition, ...] = ()
    script_id: str | None = None


def _effect_group_from_legacy(effect: MoveEffect | dict[str, Any]) -> EffectGroup:
    """Consume legacy MoveEffect.target_self into explicit effect targets."""
    if isinstance(effect, dict):
        effect = MoveEffect(**effect)

    target: EffectTarget = "self" if effect.target_self else "target"
    effects: list[Effect] = []
    if effect.status_inflict is not None:
        effects.append(StatusInflict(target=target, status=effect.status_inflict))
    if effect.stat_changes:
        effects.append(StatChange(target=target, changes=effect.stat_changes))
    return EffectGroup(chance=effect.chance, effects=tuple(effects))


class Move(_Static):
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
    effect: MoveEffect | None = None
    effects: tuple[EffectGroup, ...] = ()
    behavior: MoveBehavior = pydantic.Field(default_factory=MoveBehavior)
    target: types.MoveTargetT = types.MoveTargetT.SINGLE
    level_requirement: int = 1

    @pydantic.model_validator(mode="before")
    @classmethod
    def _migrate_legacy_effect(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("effect") is not None and not data.get("effects"):
            data = data.copy()
            data["effects"] = (_effect_group_from_legacy(data["effect"]),)
        return data

    def __hash__(self) -> int:
        """There should be no two moves named the same."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """There should be no two moves named the same."""
        if not isinstance(other, Move):
            return NotImplemented
        return self.name == other.name


# ── PERSONALITY ───────────────────────────────────────────────────────────────────────


class Vibemon(_Transient):
    """Innate properties of a Vibemon with derived actual stats."""

    nickname: str | None = None
    """The name given to the Vibemon by the Trainer."""

    affinity: Affinity
    """Represents the nature of a Vibemon, steered by the source provider.."""

    level: int
    """The Vibemon's current level."""

    birth_affinities: tuple[Affinity, ...] = ()
    """The lineage of this Vibemon's aesthetic."""

    _aesthetic: Aesthetic = pydantic.PrivateAttr()

    @classmethod
    async def birth(cls, *affinities: Affinity, nickname: str | None = None, core_identity: str | None = None) -> Self:
        """Create a Vibemon from a given context."""
        from app.genai.client import generate_vibemon_name

        if not affinities:
            raise ValueError("Vibemon must be born from at least one Affinity!")

        affinity = Affinity.merge(*affinities, core_identity_description=core_identity)

        name = await generate_vibemon_name(
            identity=affinity.identity,
            moves=affinity.moves,
            visual_notes=affinity.visual_notes,
        )

        affinity = affinity.model_copy(update={"identity": affinity.identity.model_copy(update={"name": name})})

        instance = cls(
            nickname=nickname,
            affinity=affinity,
            level=1,
            birth_affinities=affinities,
        )

        if not settings.headless:
            instance._aesthetic = Aesthetic.from_vibemon(instance)
            await instance._aesthetic.regenerate()

        return instance

    @property
    def name(self) -> str:
        """The nickname or identity name of a Vibemon."""
        return self.nickname or self.affinity.identity.name

    @property
    def elements(self) -> tuple[types.VibemonTypeT, ...]:
        """The Vibemon's elemental typing."""
        return self.affinity.identity.elements

    @property
    def aesthetic(self) -> Aesthetic:
        """The visual and aural layout of the Vibemon."""
        if not hasattr(self, "_aesthetic"):
            raise RuntimeError("You must call vibemon.birth()")

        return self._aesthetic

    @property
    def hp(self) -> int:
        """
        Calculates the actual HP stat.

        HP adds level scaling for extra survivability at higher levels.
        """
        return base_stat_level_scaling(self.affinity.identity.base_hp, level=self.level, true_floor=10)

    @property
    def attack(self) -> int:
        """Calculates the actual Attack stat."""
        return base_stat_level_scaling(self.affinity.identity.base_attack, level=self.level)

    @property
    def defense(self) -> int:
        """Calculates the actual Defense stat."""
        return base_stat_level_scaling(self.affinity.identity.base_defense, level=self.level)

    @property
    def sp_attack(self) -> int:
        """Calculates the actual Special Attack stat."""
        return base_stat_level_scaling(self.affinity.identity.base_sp_attack, level=self.level)

    @property
    def sp_defense(self) -> int:
        """Calculates the actual Special Defense stat."""
        return base_stat_level_scaling(self.affinity.identity.base_sp_defense, level=self.level)

    @property
    def speed(self) -> int:
        """Calculates the actual Speed stat."""
        return base_stat_level_scaling(self.affinity.identity.base_speed, level=self.level)


# ── BATTLE COMPATIBILITY ─────────────────────────────────────────────────────────────


_BATTLE_EXPORTS = {
    "Battle",
    "BattleTrainer",
    "BattleVibemon",
    "BattleMove",
    "FieldState",
    "FieldWeather",
    "StatStages",
    "TurnRecord",
    "BattleAction",
    "MoveAction",
    "SwitchAction",
    "ItemAction",
    "RunAction",
    "TargetRef",
    "TurnEvent",
}


def __getattr__(name: str) -> Any:
    """Lazy compatibility exports for transient battle models."""
    if name in _BATTLE_EXPORTS:
        from app.battle import actions, events
        from app.battle import schema as battle_schema

        for module in (battle_schema, actions, events):
            if hasattr(module, name):
                return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
