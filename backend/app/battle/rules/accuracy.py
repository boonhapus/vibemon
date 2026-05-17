from __future__ import annotations

from app.battle import schema as battle_schema
from app.battle import turn
from app.battle.rules import stats


def hits(ctx: turn.Turn, use: turn.MoveUse, target: battle_schema.BattleVibemon) -> bool:
    """Resolve accuracy for one target."""
    if use.move.accuracy is None:
        return True
    acc_mod = stats.accuracy_modifier(use.user.stat_stages.accuracy, target.stat_stages.evasion)
    return ctx.rng.random() <= use.move.accuracy * acc_mod
