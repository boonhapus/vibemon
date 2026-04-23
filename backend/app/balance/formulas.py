import math

from app import const


def base_stat_scaling(base_value: int, *, level: int, true_floor: int = 5) -> int:
    """
    Computes the linear scaling core for a stat.

    Formula: (2 * Base * Level / 100) + 5
      At Level 100: (2 * Base) + 5 = exact base + 5
      At Level 50: Half of species potential + 5
      +5 constant acts as true floor.
    """
    return math.floor((2 * base_value * level) / const.MAX_LEVEL) + true_floor
