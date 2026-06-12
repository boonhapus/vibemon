"""Simple opponent move selection for wild battles."""

import random

from app.domains.battle import actions, entity


def wild_move_action(
    trainer: entity.BattleTrainer,
    *,
    rng: random.Random | None = None,
) -> actions.MoveAction:
    user = trainer.active_vibemon
    move = choose_move(user, rng=rng)
    return actions.MoveAction(trainer=trainer.id, move_name=move.name)


def choose_move(
    user: entity.BattleVibemon,
    *,
    rng: random.Random | None = None,
) -> entity.BattleMove:
    usable = [move for move in user.battle_moves if move.pp_current > 0]
    if usable:
        if rng is None:
            return usable[0]
        return rng.choice(usable)
    return user.battle_moves[0]
