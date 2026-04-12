from __future__ import annotations

import random

from app.domain.stats import (
    compute_stats,
    factor_to_stat,
    make_seed,
    merge_source_data,
    scale_enemy_stats,
)
from app.domain.context import SourceData
from app.domain.models import VibemonStats


def test_make_seed_deterministic() -> None:
    assert make_seed("alice", "weather") == make_seed("alice", "weather")
    assert make_seed("alice", "weather") != make_seed("bob", "weather")


def test_factor_to_stat_range() -> None:
    rng = random.Random(42)
    for _ in range(50):
        v = factor_to_stat(0.5, rng)
        assert 1 <= v <= 255


def test_merge_averages() -> None:
    a = SourceData(hp_factor=0.2, attack_factor=0.8, element_votes=[("Fire", 0.5)])
    b = SourceData(hp_factor=0.8, defense_factor=0.4, element_votes=[("Water", 0.5)])
    m = merge_source_data([a, b])
    assert m.hp_factor == 0.5
    assert m.attack_factor == 0.8
    assert m.defense_factor == 0.4
    votes = dict(m.element_votes)
    assert votes["Fire"] == 0.5
    assert votes["Water"] == 0.5


def test_element_secondary_threshold() -> None:
    merged = SourceData(
        element_votes=[("Fire", 1.0), ("Water", 0.55)],
        hp_factor=0.5,
        attack_factor=0.5,
        defense_factor=0.5,
        sp_attack_factor=0.5,
        sp_defense_factor=0.5,
        speed_factor=0.5,
    )
    stats = compute_stats(merged, make_seed("x", "vibemon"))
    assert stats.element == "Fire"
    assert stats.element_secondary == "Water"


def test_no_secondary_below_half() -> None:
    merged = SourceData(
        element_votes=[("Fire", 1.0), ("Water", 0.4)],
        hp_factor=0.5,
        attack_factor=0.5,
        defense_factor=0.5,
        sp_attack_factor=0.5,
        sp_defense_factor=0.5,
        speed_factor=0.5,
    )
    stats = compute_stats(merged, make_seed("x", "vibemon"))
    assert stats.element_secondary is None


def test_scale_enemy_stats() -> None:
    player = VibemonStats(100, 100, 100, 100, 100, 100, "Fire", None)
    enemy_low = VibemonStats(10, 10, 10, 10, 10, 10, "Water", None)
    scaled = scale_enemy_stats(player, enemy_low)
    assert sum([scaled.hp, scaled.attack, scaled.defense, scaled.sp_attack, scaled.sp_defense, scaled.speed]) >= int(
        600 * 0.85
    )

    enemy_high = VibemonStats(200, 200, 200, 200, 200, 200, "Water", None)
    scaled2 = scale_enemy_stats(player, enemy_high)
    assert (
        sum([scaled2.hp, scaled2.attack, scaled2.defense, scaled2.sp_attack, scaled2.sp_defense, scaled2.speed])
        <= int(600 * 1.15) + 6
    )
