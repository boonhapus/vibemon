from typing import Annotated
import attrs
import cattrs

from app import types


# ---------------------------------------------------------------------------
# Vibemon
# ---------------------------------------------------------------------------


@attrs.define
class Vibemon:
    name: str
    level: int = 50
    type_list: list[types.VibemonT] = attrs.field(factory=list)

    max_hp: int = 100
    attack: int = 50
    defense: int = 50
    sp_attack: int = 50
    sp_defense: int = 50
    speed: int = 50

    current_hp: int = 100
    status: types.StatusConditionT = types.StatusConditionT.NONE
    stat_stages: types.StatStages = attrs.field(factory=types.StatStages)
    moves: list[types.Move] = attrs.field(factory=list)

    is_flinched: bool = False
    is_confused: bool = False
    confusion_turns: int = 0
    bad_poison_counter: int = 0
    sleep_turns_remaining: int = 0
    is_seeded: bool = False

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0


# ---------------------------------------------------------------------------
# Trainer / Team
# ---------------------------------------------------------------------------


@attrs.define
class Trainer:
    id: types.TrainerId
    name: str
    team: list[Vibemon] = attrs.field(factory=list)
    active_index: int = 0

    @property
    def active_vibemon(self) -> Vibemon:
        return self.team[self.active_index]

    @property
    def has_vibemon_remaining(self) -> bool:
        return any(not p.is_fainted for p in self.team)


# ---------------------------------------------------------------------------
# Turn Log
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Battle State
# ---------------------------------------------------------------------------


@attrs.define
class BattleState:
    trainer_a: Trainer
    trainer_b: Trainer
    turn_number: int = 1
    turn_history: list[TurnRecord] = attrs.field(factory=list)
    winner: types.TrainerId | None = None

    @property
    def is_over(self) -> bool:
        return self.winner is not None
