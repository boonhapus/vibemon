from __future__ import annotations

import pytest

from app.domain.models import VibemonStats
from app.domain.moves import _MOVE_POOL, generate_moves


ALL_ELEMENTS = ["Fire", "Water", "Ice", "Electric", "Grass", "Ground", "Dark", "Psychic", "Normal"]


class TestMovePools:
    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_pool_has_eight_moves(self, element: str):
        pool = _MOVE_POOL[element]
        assert len(pool) == 8, f"{element} pool has {len(pool)} moves, expected 8"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_pool_has_three_physical(self, element: str):
        pool = _MOVE_POOL[element]
        physicals = [m for m in pool if m.category == "physical"]
        assert len(physicals) == 3, f"{element} has {len(physicals)} physical moves"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_pool_has_at_least_two_special(self, element: str):
        pool = _MOVE_POOL[element]
        specials = [m for m in pool if m.category == "special"]
        assert len(specials) >= 2, f"{element} has {len(specials)} special moves"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_pool_has_two_status(self, element: str):
        pool = _MOVE_POOL[element]
        statuses = [m for m in pool if m.category == "status"]
        assert len(statuses) == 2, f"{element} has {len(statuses)} status moves"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_pool_has_one_signature(self, element: str):
        pool = _MOVE_POOL[element]
        sigs = [m for m in pool if m.is_signature]
        assert len(sigs) == 1, f"{element} has {len(sigs)} signature moves"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_all_moves_match_element_type(self, element: str):
        pool = _MOVE_POOL[element]
        for m in pool:
            assert m.type == element, f"{m.name} has type {m.type}, expected {element}"


class TestGenerateMoves:
    def _make_stats(self, element: str) -> VibemonStats:
        return VibemonStats(
            hp=120, attack=130, defense=100,
            sp_attack=140, sp_defense=110, speed=100,
            element=element,
        )

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_returns_four_moves(self, element: str):
        stats = self._make_stats(element)
        moves = generate_moves(stats, seed=42)
        assert len(moves) == 4

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_signature_always_first(self, element: str):
        stats = self._make_stats(element)
        moves = generate_moves(stats, seed=42)
        assert moves[0].is_signature, f"First move should be signature for {element}"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_has_physical_and_special(self, element: str):
        stats = self._make_stats(element)
        moves = generate_moves(stats, seed=42)
        categories = {m.category for m in moves}
        assert "physical" in categories, f"Missing physical for {element}"
        assert "special" in categories, f"Missing special for {element}"

    @pytest.mark.parametrize("element", ALL_ELEMENTS)
    def test_no_duplicate_moves(self, element: str):
        stats = self._make_stats(element)
        moves = generate_moves(stats, seed=42)
        names = [m.name for m in moves]
        assert len(names) == len(set(names)), f"Duplicate moves for {element}: {names}"

    def test_deterministic(self):
        stats = self._make_stats("Fire")
        m1 = generate_moves(stats, seed=123)
        m2 = generate_moves(stats, seed=123)
        assert [m.name for m in m1] == [m.name for m in m2]

    def test_different_seeds_may_differ(self):
        stats = self._make_stats("Fire")
        m1 = generate_moves(stats, seed=1)
        m2 = generate_moves(stats, seed=999999)
        n1 = [m.name for m in m1]
        n2 = [m.name for m in m2]
        pass


class TestDesignDocMoveNames:
    def test_dark_moves_match_spec(self):
        pool = _MOVE_POOL["Dark"]
        names = {m.name for m in pool}
        expected = {
            "Shadow Strike", "Hex Slash", "Dread Crash",
            "Curse Pulse", "Nightfall", "Void",
            "Drain", "Phantom Shroud",
        }
        assert names == expected

    def test_electric_moves_match_spec(self):
        pool = _MOVE_POOL["Electric"]
        names = {m.name for m in pool}
        expected = {
            "Spark Strike", "Volt Slam", "Thunder Crash",
            "Shock Pulse", "Discharge", "Thunderstrike",
            "Static Field", "Charge",
        }
        assert names == expected

    def test_psychic_moves_match_spec(self):
        pool = _MOVE_POOL["Psychic"]
        names = {m.name for m in pool}
        expected = {
            "Phase Strike", "Echo Bash", "Warp Crash",
            "Mind Pulse", "Distortion", "Mindbreak",
            "Foresee", "Unravel",
        }
        assert names == expected

    def test_fire_signature_is_inferno(self):
        pool = _MOVE_POOL["Fire"]
        sig = [m for m in pool if m.is_signature][0]
        assert sig.name == "Inferno"
        assert sig.power == 110
        assert sig.accuracy == 75

    def test_ground_signature_is_landslide(self):
        pool = _MOVE_POOL["Ground"]
        sig = [m for m in pool if m.is_signature][0]
        assert sig.name == "Landslide"
        assert sig.category == "physical"
        assert sig.power == 90

    def test_normal_signature_is_pummel(self):
        pool = _MOVE_POOL["Normal"]
        sig = [m for m in pool if m.is_signature][0]
        assert sig.name == "Pummel"
        assert sig.accuracy == 95
