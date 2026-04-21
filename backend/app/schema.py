from typing import Annotated, Any, Self
import datetime as dt
import math
import random
import itertools as it

import attr
import attrs
import cattrs

from app import const, types


@attrs.define
class BirthContext:
    """Represents the context in which a Vibemon is being created under."""
    seed: str
    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    weather_conditions: Any
    providers: dict[str, Affinity]


@attrs.define
class Affinity:
    """Represents a data provider's contributing to the Vibemon's nature."""
    intensity: float = 1.0
    description: str = ""
    elements: list[types.VibemonTypeT] = attrs.field(factory=list)
    base_hp: int = 120
    base_attack: int = 60
    base_defense: int = 60
    base_sp_attack: int = 60
    base_sp_defense: int = 60
    base_speed: int = 60
    moves: list[types.Move] = attrs.field(factory=list)


@attrs.define
class Vibemon:
    """Innate properties of a Vibemon with derived actual stats."""

    name: str
    description: str

    base_hp: types.BaseStat
    base_attack: types.BaseStat
    base_defense: types.BaseStat
    base_sp_attack: types.BaseStat
    base_sp_defense: types.BaseStat
    base_speed: types.BaseStat

    elements: list[types.VibemonTypeT] = attrs.field(factory=lambda: [types.VibemonTypeT.NORMAL])
    level: int = const.DEFAULT_LEVEL
    moves: list[types.Move] = attrs.field(factory=list)

    @classmethod
    def from_affinities(cls, *affinities: Affinity, name: str, description: str) -> Self:
        """Create a Vibemon from a number of affinities."""
        if not affinities:
            raise ValueError("from_affinities requires at least one Affinity")

        total_intensity = sum(a.intensity for a in affinities)

        elements: list[types.VibemonTypeT] = []
        moves: list[types.Move] = []

        base_stats = {
            "base_hp": 0,
            "base_attack": 0,
            "base_defense": 0,
            "base_sp_attack": 0,
            "base_sp_defense": 0,
            "base_speed": 0,
        }

        for affinity in sorted(affinities, key=lambda a: a.intensity, reverse=True):
            weighted_average = affinity.intensity / total_intensity

            if affinity.description:
                description += f"  {affinity.description} ({weighted_average:.2f}%)"

            if random_elements := random.sample(affinity.elements, k=random.randint(0, 2)):
                elements = list({*elements, *random_elements})[:2]

            if random_moves := random.sample(affinity.moves, k=random.randint(0, 2)):
                moves = [*moves, *random_moves][:4]

            for stat in base_stats:
                base_stats[stat] += math.floor(getattr(affinity, stat) * weighted_average)

        if not elements:
            elements = [types.VibemonTypeT.NORMAL]

        while len(moves) < const.STARTING_MOVE_COUNT:
            mpool = list(it.chain.from_iterable(a.moves for a in affinities))
            addtl = random.sample(mpool, k=const.STARTING_MOVE_COUNT - len(moves))
            moves = list({*moves, *addtl})

        return cls(
            name=name,
            description=description,
            elements=elements,
            **base_stats,
            level=1,
            moves=moves,
        )

    @property
    def visual_dna(self) -> VisualDNA:
        ...

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

    # ── Derived Properties (The "Actual" Stats) ───────────────────────────────────────

    def _calculate_core(self, base_value: int) -> int:
        """
        Computes the linear scaling core for a stat.

        Formula: (2 * Base * Level / 100) + 5
        At Level 100: (2 * Base) + 5 = exact base + 5
        At Level 50: Half of species potential + 5
        +5 constant acts as true floor.
        """
        return math.floor((2 * base_value * self.level) / const.STAT_FORMULA_LEVEL_DENOM) + const.STAT_FORMULA_ADDEND

    @property
    def hp(self) -> int:
        """
        Calculates the actual HP stat.

        HP adds level scaling for extra survivability at higher levels.
        """
        return self._calculate_core(self.base_hp) + self.level + const.HP_SCALING_OFFSET

    @property
    def attack(self) -> int:
        """Calculates the actual Attack stat."""
        return self._calculate_core(self.base_attack)

    @property
    def defense(self) -> int:
        """Calculates the actual Defense stat."""
        return self._calculate_core(self.base_defense)

    @property
    def sp_attack(self) -> int:
        """Calculates the actual Special Attack stat."""
        return self._calculate_core(self.base_sp_attack)

    @property
    def sp_defense(self) -> int:
        """Calculates the actual Special Defense stat."""
        return self._calculate_core(self.base_sp_defense)

    @property
    def speed(self) -> int:
        """Calculates the actual Speed stat."""
        return self._calculate_core(self.base_speed)


@attrs.define
class BattleVibemon(Vibemon):
    """Transient battle state layered on top of a Vibemon's innate properties.

    Separating mutable combat state (HP, status, stat stages) from the immutable
    species definition lets the engine freely mutate mid-battle values without
    risk of corrupting the underlying Vibemon data.
    """

    current_hp: int = attrs.field(default=attrs.Factory(lambda self: self.hp, takes_self=True))
    status: types.StatusConditionT = types.StatusConditionT.NONE
    stat_stages: types.StatStages = attrs.field(factory=types.StatStages)
    crit_stage: int = 0

    is_flinched: bool = False
    is_confused: bool = False
    confusion_turns: int = 0
    bad_poison_counter: int = 0
    sleep_turns_remaining: int = 0
    is_seeded: bool = False
    taunt_turns: int = 0
    bound_turns: int = 0

    @property
    def max_hp(self) -> int:
        """Delegates to the inherited HP formula so battle code has a stable reference."""
        return self.hp

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0


@attrs.define
class Trainer:
    id: types.TrainerId
    name: str
    team: list[BattleVibemon] = attrs.field(factory=list)
    active_index: int = 0

    @property
    def active_vibemon(self) -> BattleVibemon:
        return self.team[self.active_index]

    @property
    def has_vibemon_remaining(self) -> bool:
        return any(not p.is_fainted for p in self.team)


@attrs.define
class TurnEvent:
    actor: Annotated[str, "Vibemon.name"]
    description: str | None = None
    hp_delta: int | None = None
    status_change: types.StatusConditionT | None = None
    stat_stage_changes: dict[str, int] = attrs.field(factory=dict)
    move_used: str | None = None
    missed: bool = False
    fainted: bool = False


@attrs.define
class TurnRecord:
    turn_number: int
    actions: list[types.Action] = attrs.field(factory=list)
    events: list[TurnEvent] = attrs.field(factory=list)


@attrs.define
class BattleState:
    trainer_a: Trainer
    trainer_b: Trainer
    turn_number: int = 1
    turn_history: list[TurnRecord] = attrs.field(factory=list)
    winner: Trainer | None = None

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    def to_json(self) -> dict[str, Any]:
        """Serialize the battle."""
        return cattrs.unstructure(self)
