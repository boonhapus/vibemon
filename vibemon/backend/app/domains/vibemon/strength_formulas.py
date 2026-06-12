from typing import cast
import math

import structlog

from app.core.math import clamp
from app.domains.move.catalog import ELEMENT_STAT_GRADE, GRADE_WEIGHT
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.types import BaseStatNameT, EvolutionStageT

_LOGGER = structlog.get_logger(__name__)

BST_SCALING_MATRIX: dict[EvolutionStageT, list[int]] = {
    EvolutionStageT.BASE: [485],
    EvolutionStageT.STAGE_2: [300, 490],
    EvolutionStageT.STAGE_3: [280, 410, 530],
    EvolutionStageT.PSEUDO_LEGENDARY: [300, 420, 600],
    EvolutionStageT.LEGENDARY: [575],
    EvolutionStageT.ULTRA_LEGENDARY: [675],
}
"""Target BST per evolution stage for each evolution line."""


def power_pips(evo_seed: EvolutionStageT, bst: int) -> int:
    """Hatch-panel strength pips (1-3): BST vs the stage-1 target for this evo line.

    Band is ±12% around the target (upper +13% for pseudo-legendary lines, whose
    stage-1 spread skews high).
    """
    target = BST_SCALING_MATRIX[evo_seed][0]
    upper_band = 1.13 if evo_seed is EvolutionStageT.PSEUDO_LEGENDARY else 1.12
    if bst < round(target * 0.88):
        return 1
    if bst > round(target * upper_band):
        return 3
    return 2


def base_stat_level_scaling(base_value: int, *, level: int, true_floor: int = 5) -> int:
    """
    Computes the linear scaling core for a stat.

    Formula: (2 * Base * Level / 100) + 5
      At Level 100: (2 * Base) + 5 = exact base + 5
      At Level 50: Half of species potential + 5
      +5 constant acts as true floor.
    """
    return math.floor((2 * base_value * level) / 100) + true_floor


def stat_ratio_from_grade(
    signal_value: float,
    *,
    elements: tuple[VibemonTypeT, ...],
    stat: BaseStatNameT,
) -> float:
    """
    Combine an element-aware grade with a 0-1 signal value into a stat ratio.

    Grade defines the band midpoint (D=0.1, C=0.3, B=0.5, A=0.7, S=0.9). Signal
    varies within a 0.3-wide band centered on midpoint. Dual-type Vibemon average
    the two grade weights.

    Pass `signal_value` as a center-anchored mix (Signal.mix(..., mode="center")
    or signal.center) so a median city produces a median stat for its grade.
    """
    weights = [GRADE_WEIGHT[ELEMENT_STAT_GRADE[e][stat]] for e in elements]
    avg_weight = sum(weights) / len(weights)
    midpoint = (avg_weight * 2 - 1) / 10
    return clamp(midpoint + (signal_value - 0.5) * 0.3, minimum=0.0, maximum=1.0)


def base_stat_asymmetric_scaling(ratio: float, *, stat: BaseStatNameT) -> int:
    """
    Map a 0-1 ratio onto an asymmetric stat range, anchored at the median.

    ratio = 0.0 → stat.min
    ratio = 0.5 → stat.med
    ratio = 1.0 → stat.max

    Each half is scaled independently so that the median always sits
    at the midpoint of the input, regardless of how lopsided the output
    range is.
    """
    from app.domains.vibemon.identity import BaseStats

    stat_min = BaseStats._stat_info(name=stat, type="min")
    stat_med = BaseStats._stat_info(name=stat, type="med")
    stat_max = BaseStats._stat_info(name=stat, type="max")

    assert stat_min is not None, f"Stat.min is not set for {stat}"
    assert stat_med is not None, f"Stat.med is not set for {stat}"
    assert stat_max is not None, f"Stat.max is not set for {stat}"

    r = clamp(ratio, minimum=0.0, maximum=1.0)

    if r <= 0.5:
        # [0.0, 0.5] → [min, med]
        t = r / 0.5  # re-normalize to 0-1
        return int(stat_min + t * (stat_med - stat_min))
    else:
        # (0.5, 1.0] → [med, max]
        t = (r - 0.5) / 0.5
        return int(stat_med + t * (stat_max - stat_med))


def apply_evo_seed_bst_bias(
    stats: dict[str, int],
    *,
    evo_seed: EvolutionStageT,
    evo_stage: EvolutionStageT,
) -> dict[str, int]:
    """
    Re-scale base stats so total BST tracks evolution-line expectations.

    This keeps each stat's relative profile, then clamps to stat bounds and
    distributes rounding remainder to preserve the target BST when possible.
    """
    from app.domains.vibemon.identity import BaseStats

    scale_factor = BST_SCALING_MATRIX[evo_seed][evo_stage - 1] / sum(stats.values())
    scaled: dict[str, int] = {}

    for key, value in stats.items():
        stat = cast(BaseStatNameT, key)
        stat_min = BaseStats._stat_info(name=stat, type="min")
        stat_max = BaseStats._stat_info(name=stat, type="max")

        assert stat_min is not None, f"Stat.min is not set for {stat}"
        assert stat_max is not None, f"Stat.max is not set for {stat}"

        scaled[key] = math.floor(clamp(value * scale_factor, minimum=stat_min, maximum=stat_max))

    return scaled
