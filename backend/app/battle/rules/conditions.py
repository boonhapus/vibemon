from __future__ import annotations

from app import schema
from app.battle import actions, turn


def priority_delta(ctx: turn.Turn, use: turn.MoveUse) -> int:
    """Resolve declarative priority deltas."""
    delta = 0
    for condition in use.move.behavior.conditions:
        match condition:
            case schema.IfOpponentAttacking():
                opponent_action = next(
                    (
                        action
                        for key, action in ctx.actions_by_actor.items()
                        if key[0] != use.user_trainer and isinstance(action, actions.MoveAction)
                    ),
                    None,
                )
                if opponent_action is not None:
                    delta += condition.on_match.priority_delta
                elif condition.on_miss is not None:
                    delta += condition.on_miss.priority_delta
            case schema.IfWeather():
                if ctx.battle.field.weather.kind == condition.weather:
                    delta += condition.on_match.priority_delta
            case schema.IfHpBelow():
                if use.user.current_hp / use.user.max_hp < condition.threshold:
                    delta += condition.on_match.priority_delta
            case schema.RandomPower():
                continue
    return delta


def is_damaging_action(action: actions.BattleAction) -> bool:
    """Return whether an action is a move action that may damage."""
    return isinstance(action, actions.MoveAction)
