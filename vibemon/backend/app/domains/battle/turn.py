from __future__ import annotations

from typing import Literal
import random

from app.core.ids import TrainerIdT
from app.core.schema import Schema
from app.domains.battle import actions, entity, events

type PipelinePhaseName = Literal[
    "turn_start", "action_sorting", "pre_action", "execute_stack", "end_of_turn", "turn_end"
]
type ActorRef = tuple[TrainerIdT, int]


class MoveUse(Schema):
    """Resolved use of a move by an active combatant."""

    user_trainer: TrainerIdT
    user_slot: int = 0
    user: entity.BattleVibemon
    move: entity.BattleMove
    action: actions.MoveAction


class HitResult(Schema):
    """Result of one move hit against one target."""

    use: MoveUse
    target: entity.BattleVibemon
    damage: int = 0
    hit: bool = True
    damage_result: events.DamageResult | None = None


class StackEntry(Schema):
    """One action scheduled for execution."""

    trainer: TrainerIdT
    slot: int = 0
    actor: entity.BattleVibemon
    opponent: entity.BattleVibemon
    action: actions.BattleAction


class Turn:
    """Transient execution context for a submitted turn."""

    def __init__(
        self,
        *,
        battle: entity.Battle,
        rng: random.Random,
        actions_: tuple[actions.BattleAction, ...],
    ) -> None:
        self.battle = battle
        self.rng = rng
        self.actions = actions_
        self.actions_by_actor = {
            (action.trainer, getattr(action, "slot", 0)): action for action in actions_ if hasattr(action, "trainer")
        }
        self.events: list[events.TurnEvent] = []
        self.stack: list[StackEntry] = []
        self.current_entry: StackEntry | None = None
        self.phase: PipelinePhaseName = "turn_start"

    @classmethod
    def from_submit(
        cls,
        battle: entity.Battle,
        rng: random.Random,
        submitted_actions: tuple[actions.BattleAction, ...],
    ) -> Turn:
        return cls(battle=battle, rng=rng, actions_=submitted_actions)
