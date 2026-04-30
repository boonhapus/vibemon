import math

from app import const, utils, types


def base_stat_level_scaling(base_value: int, *, level: int, true_floor: int = 5) -> int:
    """
    Computes the linear scaling core for a stat.

    Formula: (2 * Base * Level / 100) + 5
      At Level 100: (2 * Base) + 5 = exact base + 5
      At Level 50: Half of species potential + 5
      +5 constant acts as true floor.
    """
    return math.floor((2 * base_value * level) / const.MAX_LEVEL) + true_floor


def base_stat_asymmetric_scaling(ratio: float, *, stat: types.BaseStatNameT) -> int:
    """
    Map a 0‑1 ratio onto an asymmetric stat range, anchored at the median.

    ratio = 0.0 → stat.min
    ratio = 0.5 → stat.med
    ratio = 1.0 → stat.max

    Each half is scaled independently so that the median always sits
    at the midpoint of the input, regardless of how lopsided the output
    range is.
    """
    from app import schema

    stat_min = schema.Identity._stat_info(name=stat, type="min")
    stat_med = schema.Identity._stat_info(name=stat, type="med")
    stat_max = schema.Identity._stat_info(name=stat, type="max")

    assert stat_min is not None, f"Stat.min is not set for {stat}"
    assert stat_med is not None, f"Stat.med is not set for {stat}"
    assert stat_max is not None, f"Stat.max is not set for {stat}"

    r = utils.clamp(ratio, minimum=0.0, maximum=1.0)

    if r <= 0.5:
        # [0.0, 0.5] → [min, med]
        t = r / 0.5  # re-normalize to 0‑1
        return int(stat_min + t * (stat_med - stat_min))
    else:
        # (0.5, 1.0] → [med, max]
        t = (r - 0.5) / 0.5
        return int(stat_med + t * (stat_max - stat_med))
