from __future__ import annotations

from typing import Literal
import random

from app import schema, types
from app.battle import actions, events
from app.battle import schema as battle_schema

type PipelinePhaseName = Literal[
    "turn_start", "action_sorting", "pre_action", "execute_stack", "end_of_turn", "turn_end"
]
type ActorRef = tuple[types.TrainerIdT, int]


class MoveUse(schema.Schema):
    """Resolved use of a move by an active combatant."""

    user_trainer: types.TrainerIdT
    user_slot: int = 0
    user: battle_schema.BattleVibemon
    move: battle_schema.BattleMove
    action: actions.MoveAction


class HitResult(schema.Schema):
    """Result of one move hit against one target."""

    use: MoveUse
    target: battle_schema.BattleVibemon
    damage: int = 0
    hit: bool = True
    damage_result: events.DamageResult | None = None


class StackEntry(schema.Schema):
    """One action scheduled for execution."""

    trainer: types.TrainerIdT
    slot: int = 0
    actor: battle_schema.BattleVibemon
    opponent: battle_schema.BattleVibemon
    action: actions.BattleAction


class Turn:
    """Transient execution context for a submitted turn."""

    def __init__(
        self,
        *,
        battle: battle_schema.Battle,
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
        battle: battle_schema.Battle,
        rng: random.Random,
        submitted_actions: tuple[actions.BattleAction, ...],
    ) -> Turn:
        return cls(battle=battle, rng=rng, actions_=submitted_actions)
