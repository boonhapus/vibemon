from app.domains.battle import actions, turn
from app.domains.move.entity import IfHpBelow, IfOpponentAttacking, IfWeather, RandomPower


def priority_delta(ctx: turn.Turn, use: turn.MoveUse) -> int:
    """Resolve declarative priority deltas."""
    delta = 0
    for condition in use.move.behavior.conditions:
        match condition:
            case IfOpponentAttacking():
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
            case IfWeather():
                if ctx.battle.field.weather.kind == condition.weather:
                    delta += condition.on_match.priority_delta
            case IfHpBelow():
                if use.user.current_hp / use.user.max_hp < condition.threshold:
                    delta += condition.on_match.priority_delta
            case RandomPower():
                continue
    return delta
