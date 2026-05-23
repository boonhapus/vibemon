import random

from app import schema, types
from app.balance.element_chart import get_move_assignment_bonus
from app.plugins.climate.provider import (
    _STARTER_WEIGHT_MAX,
    _STARTER_WEIGHT_MIN,
    _starter_move_weights,
)
from app.utils import weighted_sample


def _move(move_id: str, move_type: types.VibemonTypeT) -> schema.Move:
    return schema.Move(
        id=f"climate.{move_id}",
        name=move_id,
        flavor_text="test",
        type=move_type,
        category=types.MoveCategoryT.SPECIAL,
        level_requirement=1,
    )


def test_move_assignment_bonus_prefers_same_type_and_penalizes_antagonistic() -> None:
    elements = (types.VibemonTypeT.FIRE, types.VibemonTypeT.FLYING)
    assert get_move_assignment_bonus(types.VibemonTypeT.FIRE, elements) == 2.0
    assert get_move_assignment_bonus(types.VibemonTypeT.NORMAL, elements) == 1.0
    assert get_move_assignment_bonus(types.VibemonTypeT.GRASS, elements) == 1.5
    assert get_move_assignment_bonus(types.VibemonTypeT.PSYCHIC, elements) == 0.5


def test_starter_move_weights_are_bounded_and_keep_diversity_floor() -> None:
    moves = (
        _move("ember", types.VibemonTypeT.FIRE),
        _move("slash", types.VibemonTypeT.NORMAL),
        _move("splash", types.VibemonTypeT.WATER),
    )
    rankings = {
        types.VibemonTypeT.FIRE: 1.6,  # would exceed max after same-type bonus without cap
        types.VibemonTypeT.NORMAL: 0.8,
        types.VibemonTypeT.WATER: 0.0,  # diversity floor should keep this > 0
    }
    elements = (types.VibemonTypeT.FIRE,)

    weights = _starter_move_weights(moves=moves, rankings=rankings, elements=elements)

    assert len(weights) == 3
    assert all(_STARTER_WEIGHT_MIN <= value <= _STARTER_WEIGHT_MAX for value in weights.values())
    assert weights[moves[0]] == _STARTER_WEIGHT_MAX
    assert weights[moves[2]] == _STARTER_WEIGHT_MIN


def test_coverage_moves_outweigh_antagonistic_moves_at_equal_rankings() -> None:
    moves = (
        _move("ember", types.VibemonTypeT.FIRE),
        _move("leaf_cut", types.VibemonTypeT.GRASS),
        _move("mind_nudge", types.VibemonTypeT.PSYCHIC),
    )
    rankings = {move.type: 1.0 for move in moves}
    elements = (types.VibemonTypeT.FIRE,)

    weights = _starter_move_weights(moves=moves, rankings=rankings, elements=elements)

    assert weights[moves[0]] == 2.0
    assert weights[moves[1]] == 1.5
    assert weights[moves[2]] == 0.5


def test_starter_weighting_reduces_antagonistic_move_pick_rate() -> None:
    moves = (
        _move("ember", types.VibemonTypeT.FIRE),
        _move("leaf_cut", types.VibemonTypeT.GRASS),
        _move("mind_nudge", types.VibemonTypeT.PSYCHIC),
    )
    rankings = {move.type: 1.0 for move in moves}
    elements = (types.VibemonTypeT.FIRE,)
    weights = _starter_move_weights(moves=moves, rankings=rankings, elements=elements)
    rng = random.Random(1337)
    antagonistic_picks = 0
    total_picks = 0

    for _ in range(400):
        picks = weighted_sample(moves, [weights[move] for move in moves], k=2, rng=rng)
        antagonistic_picks += sum(move.type == types.VibemonTypeT.PSYCHIC for move in picks)
        total_picks += len(picks)

    assert antagonistic_picks / total_picks < 0.20
