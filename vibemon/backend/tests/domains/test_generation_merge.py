"""Birth merge rule tests: element fusion and final typing thresholds."""

from app.domains.generation.merge import filter_element_types, fuse_element_rankings
from app.domains.move.types import VibemonTypeT


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
