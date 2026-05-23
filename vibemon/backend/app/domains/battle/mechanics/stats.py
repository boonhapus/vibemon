from __future__ import annotations

from app.domains.battle import const, entity


def clamp_stage(stage: int) -> int:
    """Clamp stat stage to [-6, +6]."""
    return max(const.STAT_STAGE_MIN, min(const.STAT_STAGE_MAX, stage))


def _stage_multiplier(stage: int, base: int = 2) -> float:
    stage = clamp_stage(stage)
    if stage >= 0:
        return (base + stage) / base
    return base / (base + abs(stage))


def stat_stage_multiplier(stage: int) -> float:
    """Combat stat stage multiplier from -6 to +6."""
    return _stage_multiplier(stage, base=2)


def stage_modified_stat(value: int, stage: int) -> int:
    """Apply a combat stat stage and floor to an integer stat."""
    return max(1, int(value * stat_stage_multiplier(stage)))


def accuracy_modifier(accuracy_stage: int, evasion_stage: int) -> float:
    """Calculate accuracy modifier from accuracy/evasion stat stages."""
    acc_mult = _stage_multiplier(accuracy_stage, base=const.STAT_ACCURACY_DIVISOR)
    eva_mult = _stage_multiplier(evasion_stage, base=const.STAT_ACCURACY_DIVISOR)
    return acc_mult / eva_mult


def effective_speed(vibemon: entity.BattleVibemon) -> float:
    """Effective speed with current stat stages."""
    return vibemon.speed * stat_stage_multiplier(vibemon.stat_stages.speed)
