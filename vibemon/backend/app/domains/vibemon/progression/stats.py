"""Battle stat values derived from base stats and level."""

from app.domains.vibemon.identity import BaseStats
from app.domains.vibemon.strength_formulas import base_stat_level_scaling

_BATTLE_STATS = ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")


def battle_stat_at_level(base: BaseStats, stat: str, level: int) -> int:
    if stat == "hp":
        return base_stat_level_scaling(base.hp, level=level, true_floor=10) + level
    return base_stat_level_scaling(getattr(base, stat), level=level)


def stat_deltas_for_level_up(
    base: BaseStats,
    *,
    previous_level: int,
    new_level: int,
) -> tuple[dict[str, int], ...]:
    if new_level <= previous_level:
        return ()
    deltas: list[dict[str, int]] = []
    for stat in _BATTLE_STATS:
        previous = battle_stat_at_level(base, stat, previous_level)
        new = battle_stat_at_level(base, stat, new_level)
        delta = new - previous
        if delta == 0:
            continue
        deltas.append({"stat": stat, "previous": previous, "new": new, "delta": delta})
    return tuple(deltas)
