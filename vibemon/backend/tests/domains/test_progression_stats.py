"""Tests for battle stat level scaling helpers."""

from app.domains.vibemon.identity import BaseStats
from app.domains.vibemon.progression import stats as progression_stats


def test_stat_deltas_for_level_up() -> None:
    base = BaseStats(hp=45, attack=49, defense=49, sp_attack=65, sp_defense=65, speed=45)

    deltas = progression_stats.stat_deltas_for_level_up(base, previous_level=5, new_level=6)

    assert len(deltas) == 6
    hp = next(entry for entry in deltas if entry["stat"] == "hp")
    assert hp["previous"] == 19
    assert hp["new"] == 21
    assert hp["delta"] == 2


def test_stat_deltas_empty_when_level_unchanged() -> None:
    base = BaseStats(hp=45, attack=49, defense=49, sp_attack=65, sp_defense=65, speed=45)

    assert progression_stats.stat_deltas_for_level_up(base, previous_level=5, new_level=5) == ()
