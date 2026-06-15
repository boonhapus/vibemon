"""Birth merge rule tests: element fusion and final typing thresholds."""

import collections
import random

import pytest

from app.domains.generation.merge import filter_element_types, fuse_element_rankings
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.types import EvolutionStageT


def _seed_distribution(intensity: float, *, n: int = 40000) -> dict[EvolutionStageT, float]:
    rng = random.Random(0)
    counts: collections.Counter[EvolutionStageT] = collections.Counter(
        EvolutionStageT.random_seed(rng=rng, intensity=intensity) for _ in range(n)
    )
    return {stage: counts[stage] / n for stage in counts}


def test_random_seed_neutral_intensity_matches_base_distribution() -> None:
    # intensity=0.5 must leave the historical [24, 41, 34, 1] weighting intact.
    dist = _seed_distribution(0.5)
    assert dist[EvolutionStageT.BASE] == pytest.approx(0.24, abs=0.02)
    assert dist[EvolutionStageT.STAGE_2] == pytest.approx(0.41, abs=0.02)
    assert dist[EvolutionStageT.STAGE_3] == pytest.approx(0.34, abs=0.02)
    assert dist[EvolutionStageT.PSEUDO_LEGENDARY] == pytest.approx(0.01, abs=0.005)


def test_random_seed_rarity_tilts_toward_stronger_lines() -> None:
    common = _seed_distribution(0.0)
    rare = _seed_distribution(1.0)

    # Rare births shed BASE mass and gain the longer/stronger lines.
    assert rare[EvolutionStageT.BASE] < common[EvolutionStageT.BASE]
    assert rare[EvolutionStageT.STAGE_3] > common[EvolutionStageT.STAGE_3]
    assert rare[EvolutionStageT.PSEUDO_LEGENDARY] > common[EvolutionStageT.PSEUDO_LEGENDARY]


def test_fuse_element_rankings_reinforces_shared_types() -> None:
    fused = fuse_element_rankings(
        ({VibemonTypeT.WATER: 0.9, VibemonTypeT.FIRE: 0.2}, 1.0),
        ({VibemonTypeT.WATER: 0.8, VibemonTypeT.STEEL: 0.7}, 1.0),
    )

    assert fused[VibemonTypeT.WATER] > fused[VibemonTypeT.STEEL]
    assert fused[VibemonTypeT.STEEL] > 0


def test_fuse_element_rankings_preserves_single_provider_filtering() -> None:
    rankings = {VibemonTypeT.WATER: 0.9, VibemonTypeT.GRASS: 0.75, VibemonTypeT.FIRE: 0.2}
    assert filter_element_types(fuse_element_rankings((rankings, 1.0))) == filter_element_types(rankings)


def test_filter_element_types_empty_scores_default_to_normal() -> None:
    assert filter_element_types({}) == (VibemonTypeT.NORMAL,)
    assert filter_element_types({VibemonTypeT.FIRE: 0.0}) == (VibemonTypeT.NORMAL,)


def test_filter_element_types_dual_typing_requires_secondary_threshold() -> None:
    assert filter_element_types({VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.7}) == (
        VibemonTypeT.FIRE,
        VibemonTypeT.WATER,
    )
    assert filter_element_types({VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.5}) == (VibemonTypeT.FIRE,)
