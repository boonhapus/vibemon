from __future__ import annotations

import random

from app.domains.battle import actions, entity, turn
from app.domains.battle.mechanics import conditions, stats


def resolve_speed_tie(a_speed: float, b_speed: float, rng: random.Random) -> tuple[int, int]:
    """Resolve speed tie with a random bit."""
    if a_speed == b_speed:
        bit = rng.randint(0, 1)
        return (1 - bit, bit)
    return (0, 1) if a_speed >= b_speed else (1, 0)


def find_move(vibemon: entity.BattleVibemon, move_name: str) -> entity.BattleMove:
    """Look up a move by name on a vibemon."""
    for move in vibemon.battle_moves:
        if move.name == move_name:
            return move
    raise ValueError(f"{vibemon.name} has no move named {move_name!r}")


def _priority(ctx: turn.Turn, actor: entity.BattleVibemon, action: actions.BattleAction) -> int:
    if isinstance(action, actions.MoveAction):
        move = find_move(actor, action.move_name)
        use = turn.MoveUse(
            user_trainer=action.trainer,
            user_slot=action.slot,
            user=actor,
            move=move,
            action=action,
        )
        return move.priority + conditions.priority_delta(ctx, use)
    return 0


def resolve_turn_order(ctx: turn.Turn) -> list[turn.StackEntry]:
    """Return stack entries in resolution order."""
    battle = ctx.battle
    actor_a = battle.trainer_a.active_vibemon
    actor_b = battle.trainer_b.active_vibemon
    action_a = ctx.actions_by_actor[(battle.trainer_a.id, 0)]
    action_b = ctx.actions_by_actor[(battle.trainer_b.id, 0)]

    prio_a = _priority(ctx, actor_a, action_a)
    prio_b = _priority(ctx, actor_b, action_b)

    entries = [
        turn.StackEntry(
            trainer=battle.trainer_a.id,
            actor=actor_a,
            opponent=actor_b,
            action=action_a,
        ),
        turn.StackEntry(
            trainer=battle.trainer_b.id,
            actor=actor_b,
            opponent=actor_a,
            action=action_b,
        ),
    ]

    if prio_a != prio_b:
        return entries if prio_a > prio_b else [entries[1], entries[0]]

    order = resolve_speed_tie(stats.effective_speed(actor_a), stats.effective_speed(actor_b), ctx.rng)
    return [entries[order[0]], entries[order[1]]]
