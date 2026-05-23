from __future__ import annotations

from app.domains.battle import entity, turn
from app.domains.battle.mechanics import stats


def hits(ctx: turn.Turn, use: turn.MoveUse, target: entity.BattleVibemon) -> bool:
    """Resolve accuracy for one target."""
    if use.move.accuracy is None:
        return True
    acc_mod = stats.accuracy_modifier(use.user.stat_stages.accuracy, target.stat_stages.evasion)
    return ctx.rng.random() <= use.move.accuracy * acc_mod
