from __future__ import annotations

from collections import Counter
from pathlib import Path
import random
import uuid

from app import schema, types
from app.battle import actions
from app.battle import engine as battle_engine
from app.battle import events as battle_events
from app.battle import schema as battle_schema
from app.content.moves import load_provider_moves
from app.plugins.climate.provider import _starter_move_weights
from app.plugins.move_catalog import validate_move_catalog
from app.utils import weighted_sample


def _move(
    move_id: str,
    name: str,
    move_type: types.VibemonTypeT,
    *,
    category: types.MoveCategoryT = types.MoveCategoryT.PHYSICAL,
    power: int | None = 40,
) -> schema.Move:
    return schema.Move(
        id=move_id,
        name=name,
        flavor_text="Test move.",
        type=move_type,
        category=category,
        power=power,
        accuracy=1.0,
        pp=35,
        level_requirement=1,
    )


def _battle_vibemon(
    name: str,
    elements: tuple[types.VibemonTypeT, ...],
    moves: tuple[schema.Move, ...],
) -> battle_schema.BattleVibemon:
    vibemon = schema.Vibemon(
        identity=schema.Identity(name=name, elements=elements),
        moves=moves,
        level=50,
    )
    return battle_schema.BattleVibemon(**vibemon.model_dump())


def _trainer(name: str, vibemon: battle_schema.BattleVibemon) -> battle_schema.BattleTrainer:
    return battle_schema.BattleTrainer(
        id=uuid.uuid7(),
        username=name,
        team=[vibemon],
    )


def test_cross_provider_move_content_invariants_hold_globally() -> None:
    content_dir = Path("backend/app/content/moves")
    results = [load_provider_moves(path) for path in sorted(content_dir.glob("*.json"))]
    assert results, "Expected at least one provider move JSON file"
    assert all(not result.has_errors for result in results)

    all_moves = tuple(move for result in results for move in result.moves)
    validate_move_catalog(all_moves)

    # Explicitly assert global uniqueness across providers.
    ids = [move.id for move in all_moves]
    canonical_names = [move.canonical_name for move in all_moves]
    assert len(ids) == len(set(ids))
    assert len(canonical_names) == len(set(canonical_names))


def test_assignment_distribution_prefers_same_type_and_coverage_over_antagonistic() -> None:
    climate_moves = load_provider_moves(Path("backend/app/content/moves/climate.json")).moves
    starter_moves = tuple(move for move in climate_moves if move.level_requirement == 1)

    selected_by_type: dict[types.VibemonTypeT, schema.Move] = {}
    for move in starter_moves:
        selected_by_type.setdefault(move.type, move)

    move_pool = (
        selected_by_type[types.VibemonTypeT.FIRE],
        selected_by_type[types.VibemonTypeT.GRASS],
        selected_by_type[types.VibemonTypeT.PSYCHIC],
    )
    rankings = {move.type: 1.0 for move in move_pool}
    weights = _starter_move_weights(moves=move_pool, rankings=rankings, elements=(types.VibemonTypeT.FIRE,))

    assert weights[move_pool[0]] > weights[move_pool[1]] > weights[move_pool[2]]

    rng = random.Random(20260518)
    picks: list[schema.Move] = []
    for _ in range(500):
        picks.extend(weighted_sample(move_pool, [weights[move] for move in move_pool], k=2, rng=rng))

    counts = Counter(move.type for move in picks)
    assert counts[types.VibemonTypeT.FIRE] > counts[types.VibemonTypeT.GRASS] > counts[types.VibemonTypeT.PSYCHIC]


def test_battle_engine_applies_type_effectiveness_and_immunity_end_to_end() -> None:
    striker = _battle_vibemon(
        "Striker",
        (types.VibemonTypeT.FIRE,),
        (
            _move("test.flame_hit", "Flame Hit", types.VibemonTypeT.FIRE),
            _move("test.body_check", "Body Check", types.VibemonTypeT.NORMAL),
        ),
    )
    target = _battle_vibemon(
        "Target",
        (types.VibemonTypeT.GRASS, types.VibemonTypeT.GHOST),
        (_move("test.shadow_tap", "Shadow Tap", types.VibemonTypeT.GHOST),),
    )
    trainer_a = _trainer("a", striker)
    trainer_b = _trainer("b", target)
    engine = battle_engine.GameEngine(trainer_a, trainer_b, rng=random.Random(17))

    turn_one_events = engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a.id, move_name="Flame Hit"),
            actions.MoveAction(trainer=trainer_b.id, move_name="Shadow Tap"),
        ]
    )
    fire_damage_events = [
        event
        for event in turn_one_events
        if isinstance(event, battle_events.DamageEvent) and event.source == striker.name and event.move == "Flame Hit"
    ]
    assert fire_damage_events
    assert fire_damage_events[0].effectiveness == 2.0

    hp_before_immunity_turn = target.current_hp
    turn_two_events = engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a.id, move_name="Body Check"),
            actions.MoveAction(trainer=trainer_b.id, move_name="Shadow Tap"),
        ]
    )
    body_check_damage_events = [
        event
        for event in turn_two_events
        if isinstance(event, battle_events.DamageEvent) and event.source == striker.name and event.move == "Body Check"
    ]
    assert not body_check_damage_events
    assert target.current_hp == hp_before_immunity_turn
