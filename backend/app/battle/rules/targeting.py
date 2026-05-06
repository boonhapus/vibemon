from __future__ import annotations

from app import types
from app.battle import actions, turn
from app.battle import schema as battle_schema


def trainer_for_id(ctx: turn.Turn, trainer_id: types.TrainerIdT) -> battle_schema.BattleTrainer:
    """Resolve a trainer id in the current battle."""
    if ctx.battle.trainer_a.id == trainer_id:
        return ctx.battle.trainer_a
    if ctx.battle.trainer_b.id == trainer_id:
        return ctx.battle.trainer_b
    raise ValueError(f"Unknown battle trainer id {trainer_id}")


def opposing_trainer(ctx: turn.Turn, trainer_id: types.TrainerIdT) -> battle_schema.BattleTrainer:
    """Return the trainer opposing the given trainer."""
    if ctx.battle.trainer_a.id == trainer_id:
        return ctx.battle.trainer_b
    if ctx.battle.trainer_b.id == trainer_id:
        return ctx.battle.trainer_a
    raise ValueError(f"Unknown battle trainer id {trainer_id}")


def validate_actions(ctx: turn.Turn) -> None:
    """Validate one action per active 1v1 slot."""
    required = {(ctx.battle.trainer_a.id, 0), (ctx.battle.trainer_b.id, 0)}
    submitted = set(ctx.actions_by_actor)
    if submitted != required:
        raise ValueError("Battle submit requires exactly one action for each active trainer slot")


def resolve_targets(ctx: turn.Turn, use: turn.MoveUse) -> tuple[battle_schema.BattleVibemon, ...]:
    """Resolve move targets for the current 1v1 topology."""
    move = use.move
    if move.target in (types.MoveTargetT.SELF, types.MoveTargetT.USER_SIDE):
        return (use.user,)
    if move.target == types.MoveTargetT.FIELD:
        return ()

    if use.action.targets:
        resolved = []
        for target_ref in use.action.targets:
            resolved.append(trainer_for_id(ctx, target_ref.trainer).team[target_ref.slot])
        return tuple(resolved)

    return (opposing_trainer(ctx, use.user_trainer).active_vibemon,)


def make_move_use(ctx: turn.Turn, entry: turn.StackEntry, action: actions.MoveAction) -> turn.MoveUse:
    """Create a resolved MoveUse for an action."""
    from app.battle.rules import turn_order

    return turn.MoveUse(
        user_trainer=entry.trainer,
        user_slot=entry.slot,
        user=entry.actor,
        move=turn_order.find_move(entry.actor, action.move_name),
        action=action,
    )
