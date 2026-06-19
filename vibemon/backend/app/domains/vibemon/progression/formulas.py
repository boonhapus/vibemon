"""Centralized tuning constants and pure progression formulas."""

from dataclasses import dataclass
import random

from app.core.math import weighted_sample
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.progression.types import GrowthGroupT
from app.domains.vibemon.types import EvolutionStageT

MAX_LEVEL = 100

# TUNING TBD — dedicated balance pass
BASE_YIELD = 40
DIVISOR = 7
PARTICIPATION_RATIO = 0.5
TRAINER_KILL_BOOST = 1.5

EVO_SEED_XP_WEIGHT: dict[EvolutionStageT, float] = {
    EvolutionStageT.BASE: 1.0,
    EvolutionStageT.STAGE_2: 1.2,
    EvolutionStageT.STAGE_3: 1.4,
    EvolutionStageT.PSEUDO_LEGENDARY: 1.6,
}


@dataclass(frozen=True, slots=True)
class GrowthProfile:
    """Per-group XP curve coefficient and evolution milestone levels."""

    growth_coeff: int
    stage_2_level: int
    stage_3_level: int
    pseudo_stage_2_level: int
    pseudo_stage_3_level: int


# TUNING TBD — milestone levels per growth group
GROWTH_PROFILES: dict[GrowthGroupT, GrowthProfile] = {
    GrowthGroupT.FAST: GrowthProfile(
        growth_coeff=4,
        stage_2_level=14,
        stage_3_level=32,
        pseudo_stage_2_level=20,
        pseudo_stage_3_level=45,
    ),
    GrowthGroupT.MEDIUM: GrowthProfile(
        growth_coeff=5,
        stage_2_level=16,
        stage_3_level=36,
        pseudo_stage_2_level=25,
        pseudo_stage_3_level=50,
    ),
    GrowthGroupT.SLOW: GrowthProfile(
        growth_coeff=6,
        stage_2_level=20,
        stage_3_level=42,
        pseudo_stage_2_level=30,
        pseudo_stage_3_level=55,
    ),
}

# TUNING TBD — element bias for growth-rate birth rolls
ELEMENT_GROWTH_WEIGHTS: dict[VibemonTypeT, dict[GrowthGroupT, float]] = {
    VibemonTypeT.BUG: {GrowthGroupT.FAST: 3.0, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 0.4},
    VibemonTypeT.FLYING: {GrowthGroupT.FAST: 2.5, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 0.5},
    VibemonTypeT.NORMAL: {GrowthGroupT.FAST: 1.5, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 0.8},
    VibemonTypeT.DRAGON: {GrowthGroupT.FAST: 0.4, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 2.5},
    VibemonTypeT.FAIRY: {GrowthGroupT.FAST: 1.2, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 1.0},
}

_DEFAULT_ELEMENT_GROWTH_WEIGHTS: dict[GrowthGroupT, float] = {
    GrowthGroupT.FAST: 1.0,
    GrowthGroupT.MEDIUM: 1.5,
    GrowthGroupT.SLOW: 1.0,
}

# TUNING TBD — longer evolution lines skew slower maturation
EVO_SEED_GROWTH_WEIGHTS: dict[EvolutionStageT, dict[GrowthGroupT, float]] = {
    EvolutionStageT.BASE: {GrowthGroupT.FAST: 0.8, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 1.4},
    EvolutionStageT.STAGE_2: {GrowthGroupT.FAST: 1.0, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 1.1},
    EvolutionStageT.STAGE_3: {GrowthGroupT.FAST: 0.9, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 1.2},
    EvolutionStageT.PSEUDO_LEGENDARY: {GrowthGroupT.FAST: 0.7, GrowthGroupT.MEDIUM: 1.0, GrowthGroupT.SLOW: 1.5},
}


def xp_to_reach_level(level: int, *, growth_rate: GrowthGroupT) -> int:
    """Cumulative XP required to reach ``level`` (level 1 costs 0)."""
    if level <= 1:
        return 0
    coeff = GROWTH_PROFILES[growth_rate].growth_coeff
    return round(coeff * level**3)


def xp_to_next_level(*, level: int, xp: int, growth_rate: GrowthGroupT) -> int:
    """XP remaining before the next level, or 0 at max level."""
    if level >= MAX_LEVEL:
        return 0
    next_threshold = xp_to_reach_level(level + 1, growth_rate=growth_rate)
    return max(0, next_threshold - xp)


def xp_bar_ratio(*, level: int, xp: int, growth_rate: GrowthGroupT) -> float:
    """Within-level XP progress in [0, 1] using the level's XP bounds."""
    if level >= MAX_LEVEL:
        return 1.0
    floor = xp_to_reach_level(level, growth_rate=growth_rate)
    ceiling = xp_to_reach_level(level + 1, growth_rate=growth_rate)
    span = max(1, ceiling - floor)
    return min(1.0, max(0.0, (xp - floor) / span))


def level_from_total_xp(total_xp: int, *, growth_rate: GrowthGroupT) -> int:
    """Highest level whose cumulative XP threshold is met by ``total_xp``."""
    level = 1
    while level < MAX_LEVEL and xp_to_reach_level(level + 1, growth_rate=growth_rate) <= total_xp:
        level += 1
    return level


def xp_award_for_faint(
    *,
    opponent_level: int,
    opponent_evo_seed: EvolutionStageT,
    opponent_is_trainer_owned: bool,
) -> int:
    """Full killer share for one fainted opponent."""
    weight = EVO_SEED_XP_WEIGHT.get(opponent_evo_seed, 1.0)
    xp = round(BASE_YIELD * opponent_level * weight / DIVISOR)
    if opponent_is_trainer_owned:
        xp = round(xp * TRAINER_KILL_BOOST)
    return max(0, xp)


def participation_share(full_share: int) -> int:
    """Per-participant slice of the participation pool for one faint."""
    if full_share <= 0:
        return 0
    return max(1, round(full_share * PARTICIPATION_RATIO))


def evolution_milestones(*, growth_rate: GrowthGroupT, evo_seed: EvolutionStageT) -> tuple[int, ...]:
    """Level thresholds that promote ``evo_stage`` along an ``evo_seed`` line."""
    if evo_seed is EvolutionStageT.BASE:
        return ()
    profile = GROWTH_PROFILES[growth_rate]
    match evo_seed:
        case EvolutionStageT.STAGE_2:
            return (profile.stage_2_level,)
        case EvolutionStageT.STAGE_3:
            return (profile.stage_2_level, profile.stage_3_level)
        case EvolutionStageT.PSEUDO_LEGENDARY:
            return (profile.pseudo_stage_2_level, profile.pseudo_stage_3_level)
        case _:
            return ()


def stage_at_level(
    *,
    level: int,
    growth_rate: GrowthGroupT,
    evo_seed: EvolutionStageT,
) -> EvolutionStageT:
    """Highest ``evo_stage`` earned at ``level`` for an ``evo_seed`` line."""
    milestones = evolution_milestones(growth_rate=growth_rate, evo_seed=evo_seed)
    stage = EvolutionStageT.BASE
    stage_order = (
        EvolutionStageT.BASE,
        EvolutionStageT.STAGE_2,
        EvolutionStageT.STAGE_3,
    )
    for milestone, next_stage in zip(milestones, stage_order[1 : len(milestones) + 1], strict=False):
        if level >= milestone:
            stage = next_stage
    return stage


def pending_evolution_stage(
    *,
    level: int,
    growth_rate: GrowthGroupT,
    evo_seed: EvolutionStageT,
    current_stage: EvolutionStageT,
) -> EvolutionStageT | None:
    """Target stage if the mon is past a milestone but has not promoted yet."""
    earned = stage_at_level(level=level, growth_rate=growth_rate, evo_seed=evo_seed)
    if earned.value > current_stage.value:
        return earned
    return None


def roll_growth_rate(
    *,
    rng: random.Random,
    evo_seed: EvolutionStageT,
    elements: tuple[VibemonTypeT, ...],
) -> GrowthGroupT:
    """Weighted birth roll biased by dominant element and evolution line."""
    groups = tuple(GrowthGroupT)
    weights: list[float] = []
    seed_weights = EVO_SEED_GROWTH_WEIGHTS.get(evo_seed, _DEFAULT_ELEMENT_GROWTH_WEIGHTS)
    element_weights = [ELEMENT_GROWTH_WEIGHTS.get(element, _DEFAULT_ELEMENT_GROWTH_WEIGHTS) for element in elements]
    for group in groups:
        element_factor = sum(row[group] for row in element_weights) / len(element_weights) if element_weights else 1.0
        entropy = 0.85 + rng.random() * 0.3
        weights.append(seed_weights.get(group, 1.0) * element_factor * entropy)
    return weighted_sample(groups, weights, k=1, rng=rng)[0]
