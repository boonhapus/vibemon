import random

import pytest

from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.providers.helpers import pick_starter_moves


def _move(
    move_id: str,
    move_type: VibemonTypeT,
    *,
    level_requirement: int = 1,
    category: MoveCategoryT = MoveCategoryT.PHYSICAL,
    power: int | None = 40,
) -> Move:
    return Move(
        id=move_id,
        name=move_id.replace(".", " "),
        flavor_text="test move",
        type=move_type,
        category=category,
        power=power,
        level_requirement=level_requirement,
    )


def test_pick_starter_moves_selects_exactly_k_level_one_moves() -> None:
    moves = (
        _move("test.fire_one", VibemonTypeT.FIRE),
        _move("test.water_one", VibemonTypeT.WATER),
        _move("test.normal_one", VibemonTypeT.NORMAL),
        _move("test.fire_late", VibemonTypeT.FIRE, level_requirement=5),
    )

    selected = pick_starter_moves(
        moves=moves,
        rankings={VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.5},
        elements=(VibemonTypeT.FIRE,),
        k=2,
        rng=random.Random(1),
    )

    assert len(selected) == 2
    assert len(set(selected)) == 2
    assert {move.id for move in selected} <= {"test.fire_one", "test.water_one", "test.normal_one"}


def test_pick_starter_moves_raises_when_k_exceeds_candidate_pool() -> None:
    moves = (
        _move("test.fire_one", VibemonTypeT.FIRE),
        _move("test.fire_late", VibemonTypeT.FIRE, level_requirement=5),
    )

    with pytest.raises(ValueError, match="Cannot select 2 starter moves from 1 eligible starter moves"):
        pick_starter_moves(
            moves=moves,
            rankings={VibemonTypeT.FIRE: 1.0},
            elements=(VibemonTypeT.FIRE,),
            k=2,
            rng=random.Random(1),
        )


def test_pick_starter_moves_raises_when_no_damaging_candidates() -> None:
    moves = (
        _move("test.status_one", VibemonTypeT.NORMAL, category=MoveCategoryT.STATUS, power=None),
        _move("test.status_two", VibemonTypeT.FIRE, category=MoveCategoryT.STATUS, power=None),
    )

    with pytest.raises(ValueError, match="without at least one damaging move"):
        pick_starter_moves(
            moves=moves,
            rankings={VibemonTypeT.FIRE: 1.0},
            elements=(VibemonTypeT.FIRE,),
            k=2,
            rng=random.Random(1),
        )


def test_pick_starter_moves_always_includes_one_damaging_move() -> None:
    status_moves = tuple(
        _move(
            f"test.status_{index}",
            VibemonTypeT.NORMAL,
            category=MoveCategoryT.STATUS,
            power=None,
        )
        for index in range(9)
    )
    moves = (*status_moves, _move("test.fire_one", VibemonTypeT.FIRE))

    for seed in range(20):
        selected = pick_starter_moves(
            moves=moves,
            rankings={VibemonTypeT.FIRE: 1.0, VibemonTypeT.NORMAL: 0.1},
            elements=(VibemonTypeT.FIRE,),
            k=10,
            rng=random.Random(seed),
        )

        assert len(selected) == 10
        assert any(move.deals_damage for move in selected)
