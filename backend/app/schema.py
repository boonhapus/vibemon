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
    base_hp: int         = pydantic.Field(default=70, ge= 1, le=255, json_schema_extra={"min":  1, "med": 70, "max": 255})
    base_attack: int     = pydantic.Field(default=75, ge= 5, le=190, json_schema_extra={"min":  5, "med": 75, "max": 190})
    base_defense: int    = pydantic.Field(default=70, ge= 5, le=230, json_schema_extra={"min":  5, "med": 70, "max": 230})
    base_sp_attack: int  = pydantic.Field(default=70, ge=10, le=194, json_schema_extra={"min": 10, "med": 70, "max": 194})
    base_sp_defense: int = pydantic.Field(default=70, ge=20, le=230, json_schema_extra={"min": 20, "med": 70, "max": 230})
    base_speed: int      = pydantic.Field(default=70, ge= 5, le=200, json_schema_extra={"min":  5, "med": 70, "max": 200})

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
            moves    = utils.weighted_sample(*zip(*pop_m), k=random.randint(2, min(3, len(pop_m))))
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


# ── BATTLE ────────────────────────────────────────────────────────────────────────────


class BattleAction(_Static):
    """An action selected by a trainer to perform during their turn."""

    trainer_name: types.TrainerIdT
    action_type: types.ActionTypeT
    value: str


class TurnEvent(_Static):
    """Represents the result of an action taken of a Vibemon battle."""

    actor: Annotated[str | None, "Vibemon.name"]
    description: str | None = None
    hp_delta: int | None = None
    status_change: types.StatusConditionT | None = None
    stat_stage_changes: dict[str, int] = pydantic.Field(default_factory=dict)
    move_used: str | None = None
    missed: bool = False
    fainted: bool = False


class TurnRecord(_Transient):
    """Represents a specific turn of a Vibemon battle."""

    turn_number: int
    actions: list[BattleAction] = pydantic.Field(default_factory=list)
    events: list[TurnEvent] = pydantic.Field(default_factory=list)


class Battle(_Transient):
    """Represents the state of a Vibemon battle."""

    trainer_a: BattleTrainer
    trainer_b: BattleTrainer
    turn_number: int = 1
    turn_history: list[TurnRecord] = pydantic.Field(default_factory=list)
    winner: BattleTrainer | None = None

    @property
    def concluded(self) -> bool:
        """Determines if the battle is over."""
        return self.winner is not None

    def to_json(self) -> dict[str, Any]:
        """Serialize the battle."""
        return self.model_dump(mode="json")


class BattleMove(Move, frozen=False, validate_assignment=True):
    """
    Transient battle state layed on top of a Move.
    """

    pp_current: int = -1
    priority: int = 0
    crit_ratio: int = 0

    @pydantic.model_validator(mode="after")
    def _set_current_pp_if_not_default(self) -> Self:
        if self.pp_current == -1:
            self.pp_current = self.pp

        return self


class StatStages(_Transient):
    """Stat stage modifiers accumulated during battle, ranging from -6 to +6."""

    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


class BattleTrainer(Trainer, frozen=False, validate_assignment=True):
    """
    Transient battle state layed on top of a Trainer.
    """

    active_index: int = 0
    team: list[BattleVibemon] = pydantic.Field(default_factory=list)

    @property
    def active_vibemon(self) -> BattleVibemon:
        """Which Vibemon should be out on the field?"""
        return self.team[self.active_index]

    @property
    def has_vibemon_remaining(self) -> bool:
        """Which does this trainer have any Vibemon to fight?"""
        return any(not p.is_fainted for p in self.team)


class BattleVibemon(Vibemon, frozen=False, validate_assignment=True):
    """
    Transient battle state layered on top of a Vibemon's innate properties.
    """

    current_hp: int = 0
    moves: list[BattleMove] = pydantic.Field(default_factory=list)
    status: types.StatusConditionT = types.StatusConditionT.NONE
    stat_stages: StatStages = pydantic.Field(default_factory=StatStages)
    crit_stage: int = 0

    is_flinched: bool = False
    is_confused: bool = False
    confusion_turns: int = 0
    bad_poison_counter: int = 0
    sleep_turns_remaining: int = 0
    is_seeded: bool = False
    taunt_turns: int = 0
    bound_turns: int = 0

    @pydantic.model_validator(mode="after")
    def _apply_battle_defaults(self) -> Self:
        """Initialize transient battle state from the underlying Vibemon."""
        if self.current_hp == 0:
            self.current_hp = self.hp

        if not self.moves:
            self.moves = [BattleMove(**move.model_dump()) for move in self.affinity.moves]

        return self

    @property
    def max_hp(self) -> int:
        """Delegates to the inherited HP formula so battle code has a stable reference."""
        return self.hp

    @property
    def is_fainted(self) -> bool:
        """Is the Vibemon fainted."""
        return self.current_hp <= 0
