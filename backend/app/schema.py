from typing import Annotated, Any
import math

import attrs
import cattrs

from app import types


@attrs.define
class Vibemon:
    """Innate properties of a Vibemon with derived actual stats."""
    name: str

    base_hp: int
    base_attack: int
    base_defense: int
    base_sp_attack: int
    base_sp_defense: int
    base_speed: int

    type_list: list = attrs.field(factory=list)
    level: int = 1
    moves: list[types.Move] = attrs.field(factory=list)

    @property
    def bst(self) -> int:
        """
        The Base Stat Total (BST).
        
        Calculates the sum of all six base stats to provide a single value 
        representing the species' overall power tier.
        """
        return (
            self.base_hp + 
            self.base_attack + 
            self.base_defense + 
            self.base_sp_attack + 
            self.base_sp_defense + 
            self.base_speed
        )

    # ── Derived Properties (The "Actual" Stats) ───────────────────────────────────────

    def _calculate_core(self, base_value: int) -> int:
        """
        Computes the linear scaling core for a stat.
        
        The formula (2 * Base * Level / 100) + 5 is designed so that:
          1. At Level 100, the stat is exactly (2 * Base) + 5, making the base an intuitive predictor of endgame power.
          2. At Level  50, the stat is exactly half of its species potential.
          3. The +5 constant acts as a true floor.
        """
        return math.floor((2 * base_value * self.level) / 100) + 5

    @property
    def hp(self) -> int:
        """
        Calculates the actual HP stat.
        
        Unlike other stats, HP scales with an additional buffer to
        ensure enough survivability to participate in low level combat.
        """
        return self._calculate_core(self.base_hp) + self.level + 5

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