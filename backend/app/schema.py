from typing import Annotated, Any, Self
import datetime as dt
import math
import random

from pydantic import BaseModel, ConfigDict, model_validator
import pydantic

from app.balance.formulas import base_stat_scaling
from app.plugins.base import Base
from app import const, types, validators


# ── INTERNALS ─────────────────────────────────────────────────────────────────────────

class _Static(BaseModel):
    """Base configuration for all models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )


class _Transient(BaseModel):
    """Base configuration for all models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=False,
    )


# ── SEED ──────────────────────────────────────────────────────────────────────────────

class BirthContext(_Static, arbitrary_types_allowed=True):
    """Represents the context in which a Vibemon is being created under."""

    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    providers: dict[str, Base]


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

    elements: tuple[types.VibemonTypeT, ...] = ()
    base_hp: int = 110
    base_attack: int = 50
    base_defense: int = 50
    base_sp_attack: int = 50
    base_sp_defense: int = 50
    base_speed: int = 50

    evo_seed: int = pydantic.Field(default_factory=lambda: random.randint(1, 3))
    """The number of evolutions for this Vibemon."""

    evo_stage: types.EvolutionStageT = types.EvolutionStageT.BASE
    """The current evolution of this Vibemon."""

    is_mythic: bool = pydantic.Field(default_factory=lambda: random.randint(1, const.MYTHIC_ODDS) == const.MYTHIC_ODDS)
    """A rare, alternative style that differs from its peer identities' appearance."""

    @classmethod
    def null_identity(cls) -> Self:
        """Generates the NULL identity, for base stat manipulation."""
        return cls(name="NULL", evo_seed=1, is_mythic=False)

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


class Affinity(_Static):
    """Represents the nature of a Vibemon, steered by the source provider.."""

    identity: Identity
    """Represents the core, immutable personality of a Vibemon."""

    visual_notes: str | None = None
    """Supplied by a data provider."""

    intensity: float = 1.0
    """The mangitude of the steering relative to other providers."""

    provider_id: str
    """The source of steering."""

    moves: list[Move]


class Aesthetic(_Static):
    """ """

    bg_hex: str = "#C47A7A"
    """Background color for more effective chroma-keying."""

    async def render(self, vibemon) -> bytes:
        """ """
        from app.genai.client import generate_vibemon_sprite

        b = await generate_vibemon_sprite(vibemon=vibemon, bg_hex=self.bg_hex)
        return b


# ── MOVES ─────────────────────────────────────────────────────────────────────────────

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


class MoveEffect(_Static):
    """Secondary effects that may occur when a move is used."""

    status_inflict: types.StatusConditionT | None = None
    stat_changes: dict[types.BaseStatNameT, int] = pydantic.Field(default_factory=dict)
    target_self: bool = False
    chance: float = 1.0


# ── PERSONALITY ───────────────────────────────────────────────────────────────────────

class Vibemon(_Transient):
    """Innate properties of a Vibemon with derived actual stats."""

    nickname: str | None = None
    """The name given to the Vibemon by the Trainer."""

    affinity: Affinity
    """Represents the nature of a Vibemon, steered by the source provider.."""

    level: int = const.DEFAULT_LEVEL
    """The Vibemon's current level."""

    birth_affinities: tuple[Affinity, ...] = ()
    """Immutable per-provider identities captured at merge time. Drives visual DNA."""

    @classmethod
    def merge_affinities(cls, *affinities: Affinity, nickname: str | None = None, description: str | None = None) -> Self:
        """Create a Vibemon from a number of affinities."""
        if not affinities:
            raise ValueError("from_affinities requires at least one Affinity")

        stat_keys = (
            "base_hp",
            "base_attack",
            "base_defense",
            "base_sp_attack",
            "base_sp_defense",
            "base_speed",
        )

        name  = ""
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
        
        stats_merged = {k: math.floor(stats[k] / total) for k in stat_keys}
        elements = random.sample([e for (e, _) in pop_e], k=random.randint(1, 2), counts=[i for (_, i) in pop_e])
        moves    = random.sample([e for (e, _) in pop_m], k=random.randint(2, 3), counts=[i for (_, i) in pop_m])

        merged_affinity = Affinity(
            identity=Identity(
                name=name,
                visual_notes=description,
                elements=tuple(set(elements)),
                **stats_merged,  # type: ignore
            ),
            visual_notes=" ".join(notes),
            provider_id="merged",
            intensity=1,
            moves=moves,
        )

        return cls(
            nickname=nickname,
            affinity=merged_affinity,
            level=1,
            birth_affinities=affinities,
        )
    
    @property
    def name(self) -> str:
        """The nickname or identity name of a Vibemon."""
        return self.nickname or self.affinity.identity.name

    @property
    def hp(self) -> int:
        """
        Calculates the actual HP stat.

        HP adds level scaling for extra survivability at higher levels.
        """
        return base_stat_scaling(self.affinity.identity.base_hp, level=self.level, true_floor=10)

    @property
    def attack(self) -> int:
        """Calculates the actual Attack stat."""
        return base_stat_scaling(self.affinity.identity.base_attack, level=self.level)

    @property
    def defense(self) -> int:
        """Calculates the actual Defense stat."""
        return base_stat_scaling(self.affinity.identity.base_defense, level=self.level)

    @property
    def sp_attack(self) -> int:
        """Calculates the actual Special Attack stat."""
        return base_stat_scaling(self.affinity.identity.base_sp_attack, level=self.level)

    @property
    def sp_defense(self) -> int:
        """Calculates the actual Special Defense stat."""
        return base_stat_scaling(self.affinity.identity.base_sp_defense, level=self.level)

    @property
    def speed(self) -> int:
        """Calculates the actual Speed stat."""
        return base_stat_scaling(self.affinity.identity.base_speed, level=self.level)


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


class TurnRecord(_Static):
    """Represents a specific turn of a Vibemon battle."""

    turn_number: int
    actions: list[BattleAction] = pydantic.Field(default_factory=list)
    events: list[TurnEvent] = pydantic.Field(default_factory=list)


class Battle(_Transient):
    """Represents the state of a Vibemon battle."""

    trainer_a: Trainer
    trainer_b: Trainer
    turn_number: int = 1
    turn_history: list[TurnRecord] = pydantic.Field(default_factory=list)
    winner: Trainer | None = None

    @property
    def concluded(self) -> bool:
        """Determines if the battle is over."""
        return self.winner is not None

    def to_json(self) -> dict[str, Any]:
        """Serialize the battle."""
        return self.model_dump(mode="json")


class BattleMove(Move, frozen=False):
    """
    Transient battle state layed on top of a Move.
    """

    pp_current: int = -1
    priority: int = 0
    crit_ratio: int = 0

    @model_validator(mode='after')
    def _set_current_pp_if_not_default(self) -> BattleMove:
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


class BattleTrainer(Trainer, frozen=False):
    """
    Transient battle state layed on top of a Trainer.
    """

    active_index: int = 0
    team: list[BattleVibemon] = pydantic.Field(default_factory=list)  # type: ignore

    @property
    def active_vibemon(self) -> BattleVibemon:
        """Which Vibemon should be out on the field?"""
        return self.team[self.active_index]

    @property
    def has_vibemon_remaining(self) -> bool:
        """Which does this trainer have any Vibemon to fight?"""
        return any(not p.is_fainted for p in self.team)


class BattleVibemon(Vibemon, frozen=False):
    """
    Transient battle state layered on top of a Vibemon's innate properties.
    """

    current_hp: int = 0
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

    @model_validator(mode="before")
    @classmethod
    def _apply_current_hp_if_not_given(cls, data: Any) -> Any:
        """You can't create a Vibemon who is Fainted."""
        if data["current_hp"] == 0:
            data["current_hp"] = data["hp"]

        return data

    @property
    def max_hp(self) -> int:
        """Delegates to the inherited HP formula so battle code has a stable reference."""
        return self.hp

    @property
    def is_fainted(self) -> bool:
        """Is the Vibemon fainted."""
        return self.current_hp <= 0
