import random
import uuid

import pytest

from app.domains.battle import actions, engine, entity, events
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.identity import BaseStats, Identity


def test_battle_engine_resolves_damage_and_winner() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    strike = Move(
        id="test.heavy_strike",
        name="Heavy Strike",
        flavor_text="A test hit.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=120,
        accuracy=1.0,
    )
    tap = Move(
        id="test.tap",
        name="Tap",
        flavor_text="A test tap.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=1,
        accuracy=1.0,
    )
    attacker = entity.BattleVibemon(
        identity=Identity(
            name="Attacker",
            elements=(VibemonTypeT.NORMAL,),
            base=BaseStats(attack=190, speed=200),
        ),
        moves=(strike,),
        level=50,
    )
    defender = entity.BattleVibemon(
        identity=Identity(
            name="Defender",
            elements=(VibemonTypeT.NORMAL,),
            base=BaseStats(hp=1, defense=5, speed=5),
        ),
        moves=(tap,),
        level=1,
    )
    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", team=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", team=[defender]),
        rng=random.Random(1),
    )

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Heavy Strike"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Tap"),
        ]
    )

    assert any(isinstance(event, events.DamageEvent) for event in turn_events)
    assert any(isinstance(event, events.FaintEvent) and event.target == "Defender" for event in turn_events)
    assert battle_engine.battle.winner is not None
    assert battle_engine.battle.winner.id == trainer_a_id
    assert battle_engine.battle.turn_number == 2


def test_battle_engine_requires_one_action_per_active_trainer() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    move = Move(
        id="test.tap",
        name="Tap",
        flavor_text="A test tap.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=40,
    )

    def vibemon(name: str) -> entity.BattleVibemon:
        return entity.BattleVibemon(
            identity=Identity(name=name, elements=(VibemonTypeT.NORMAL,), base=BaseStats()),
            moves=(move,),
        )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", team=[vibemon("A")]),
        entity.BattleTrainer(id=trainer_b_id, username="b", team=[vibemon("B")]),
    )

    with pytest.raises(ValueError, match="exactly one action"):
        battle_engine.submit_actions([actions.MoveAction(trainer=trainer_a_id, move_name="Tap")])


def test_move_fails_when_selected_move_has_no_pp_but_other_moves_exist() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    empty_move = Move(
        id="test.empty_move",
        name="Empty Move",
        flavor_text="No PP left.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=40,
        pp=1,
    )
    backup = Move(
        id="test.backup",
        name="Backup",
        flavor_text="Still has PP.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=40,
        pp=10,
    )
    enemy = Move(
        id="test.enemy_tap",
        name="Enemy Tap",
        flavor_text="A test tap.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=1,
    )

    attacker = entity.BattleVibemon(
        identity=Identity(name="Attacker", elements=(VibemonTypeT.NORMAL,), base=BaseStats()),
        moves=(empty_move, backup),
        level=25,
    )
    attacker.battle_moves[0].pp_current = 0

    defender = entity.BattleVibemon(
        identity=Identity(name="Defender", elements=(VibemonTypeT.NORMAL,), base=BaseStats()),
        moves=(enemy,),
        level=25,
    )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", team=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", team=[defender]),
        rng=random.Random(1),
    )

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Empty Move"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Enemy Tap"),
        ]
    )

    assert any(
        isinstance(event, events.MoveFailedEvent)
        and event.user == "Attacker"
        and event.move == "Empty Move"
        and event.reason == "no_pp"
        for event in turn_events
    )
    assert not any(
        isinstance(event, events.MoveUsedEvent) and event.user == "Attacker" and event.move == "Breaking Point"
        for event in turn_events
    )


def test_breaking_point_auto_used_when_all_moves_are_depleted() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    dry_1 = Move(
        id="test.dry_one",
        name="Dry One",
        flavor_text="No PP left.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=40,
        pp=1,
    )
    dry_2 = Move(
        id="test.dry_two",
        name="Dry Two",
        flavor_text="No PP left.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=40,
        pp=1,
    )
    enemy = Move(
        id="test.enemy_nudge",
        name="Enemy Nudge",
        flavor_text="A test nudge.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=1,
    )

    attacker = entity.BattleVibemon(
        identity=Identity(name="Attacker", elements=(VibemonTypeT.NORMAL,), base=BaseStats(hp=120)),
        moves=(dry_1, dry_2),
        level=30,
    )
    attacker.battle_moves[0].pp_current = 0
    attacker.battle_moves[1].pp_current = 0
    hp_before = attacker.current_hp

    defender = entity.BattleVibemon(
        identity=Identity(name="Defender", elements=(VibemonTypeT.NORMAL,), base=BaseStats(hp=120)),
        moves=(enemy,),
        level=30,
    )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", team=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", team=[defender]),
        rng=random.Random(1),
    )

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Dry One"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Enemy Nudge"),
        ]
    )

    assert any(
        isinstance(event, events.MoveUsedEvent) and event.user == "Attacker" and event.move == "Breaking Point"
        for event in turn_events
    )
    assert attacker.current_hp < hp_before
