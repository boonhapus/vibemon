from typing import NamedTuple, Final
import math

from app import const, utils


class _StatRange(NamedTuple):
    min: int
    med: int
    max: int


_STAT_RANGES: Final[dict[str, _StatRange]] = {
    "base_hp":         _StatRange(  1, 70, 255),
    "base_attack":     _StatRange(  5, 75, 190),
    "base_defense":    _StatRange(  5, 70, 230),
    "base_sp_attack":  _StatRange( 10, 70, 194),
    "base_sp_defense": _StatRange( 20, 70, 230),
    "base_speed":      _StatRange(  5, 70, 200),
}


def base_stat_level_scaling(base_value: int, *, level: int, true_floor: int = 5) -> int:
    """
    Computes the linear scaling core for a stat.

    Formula: (2 * Base * Level / 100) + 5
      At Level 100: (2 * Base) + 5 = exact base + 5
      At Level 50: Half of species potential + 5
      +5 constant acts as true floor.
    """
    return math.floor((2 * base_value * level) / const.MAX_LEVEL) + true_floor


def base_stat_asymmetric_scaling(ratio: float, stat: str) -> int:
    """
    Map a 0‑1 ratio onto an asymmetric stat range, anchored at the median.

    ratio = 0.0 → stat.min
    ratio = 0.5 → stat.med
    ratio = 1.0 → stat.max

    Each half is scaled independently so that the median always sits
    at the midpoint of the input, regardless of how lopsided the
    output range is.
    """
    r = utils.clamp(ratio, minimum=0.0, maximum=1.0)
    s = _STAT_RANGES[stat]

    if r <= 0.5:
        # [0.0, 0.5] → [min, med]
        t = r / 0.5  # re-normalize to 0‑1
        return int(s.min + t * (s.med - s.min))
    else:
        # (0.5, 1.0] → [med, max]
        t = (r - 0.5) / 0.5
        return int(s.med + t * (s.max - s.med))
