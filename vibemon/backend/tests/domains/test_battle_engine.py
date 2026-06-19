import random
import uuid

import pytest

from app.domains.battle import actions, engine, entity, events
from app.domains.move.entity import EffectGroup, Move, StatChange
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.identity import BaseStats, Identity
from app.http import battle_read


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
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
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
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[vibemon("A")]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[vibemon("B")]),
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
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
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

    defender = entity.BattleVibemon(
        identity=Identity(name="Defender", elements=(VibemonTypeT.NORMAL,), base=BaseStats(hp=120)),
        moves=(enemy,),
        level=30,
    )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
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
    expected_recoil = max(1, int(attacker.max_hp * 0.25))
    recoil_events = [
        event
        for event in turn_events
        if isinstance(event, events.DamageEvent) and event.source == "Attacker" and event.target == "Attacker"
    ]
    assert len(recoil_events) == 1
    assert recoil_events[0].amount == expected_recoil


def test_status_move_emits_move_used_before_stat_change() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    intimidate = Move(
        id="test.intimidate",
        name="Intimidate",
        flavor_text="Lowers attack.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.STATUS,
        power=None,
        accuracy=1.0,
        effects=(
            EffectGroup(
                trigger="on_hit",
                chance=1.0,
                effects=(StatChange(changes={"attack": -1}),),
            ),
        ),
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
            base=BaseStats(speed=200),
        ),
        moves=(intimidate,),
        level=25,
    )
    defender = entity.BattleVibemon(
        identity=Identity(
            name="Defender",
            elements=(VibemonTypeT.NORMAL,),
            base=BaseStats(speed=5),
        ),
        moves=(tap,),
        level=25,
    )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
        rng=random.Random(1),
    )

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Intimidate"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Tap"),
        ]
    )

    move_used_index = next(i for i, event in enumerate(turn_events) if event.kind == "move_used")
    stat_change_index = next(i for i, event in enumerate(turn_events) if event.kind == "stat_change")
    assert move_used_index < stat_change_index

    messages = battle_read.events_to_messages(
        turn_events,
        hero_name="Attacker",
        wild_name="Defender",
    )
    assert messages[move_used_index] == "Attacker used Intimidate!"
    assert messages[stat_change_index] == "Their Attack has dropped!"


def test_single_target_self_buff_applies_on_use_stat_change() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    blessing = Move(
        id="test.triplicity_blessing",
        name="Triplicity Blessing",
        flavor_text="Raises the user's Special Attack.",
        type=VibemonTypeT.FLYING,
        category=MoveCategoryT.STATUS,
        power=None,
        accuracy=1.0,
        effects=(
            EffectGroup(
                trigger="on_use",
                chance=1.0,
                effects=(StatChange(target="self", changes={"sp_attack": 1}),),
            ),
        ),
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
            elements=(VibemonTypeT.FLYING,),
            base=BaseStats(speed=200),
        ),
        moves=(blessing,),
        level=25,
    )
    defender = entity.BattleVibemon(
        identity=Identity(
            name="Defender",
            elements=(VibemonTypeT.NORMAL,),
            base=BaseStats(speed=5),
        ),
        moves=(tap,),
        level=25,
    )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
        rng=random.Random(1),
    )

    assert attacker.stat_stages.sp_attack == 0

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Triplicity Blessing"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Tap"),
        ]
    )

    assert attacker.stat_stages.sp_attack == 1
    assert any(
        isinstance(event, events.StatChangeEvent) and event.target == "Attacker" and event.changes.get("sp_attack") == 1
        for event in turn_events
    )


def test_stat_change_skipped_when_damage_kos_target() -> None:
    trainer_a_id = uuid.uuid7()
    trainer_b_id = uuid.uuid7()
    crushing = Move(
        id="test.crushing_blow",
        name="Crushing Blow",
        flavor_text="Hits hard and lowers defense.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=120,
        accuracy=1.0,
        effects=(
            EffectGroup(
                trigger="after_damage",
                chance=1.0,
                effects=(StatChange(changes={"defense": -1}),),
            ),
        ),
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
        moves=(crushing,),
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
        entity.BattleTrainer(id=trainer_a_id, username="a", crew=[attacker]),
        entity.BattleTrainer(id=trainer_b_id, username="b", crew=[defender]),
        rng=random.Random(1),
    )

    turn_events = battle_engine.submit_actions(
        [
            actions.MoveAction(trainer=trainer_a_id, move_name="Crushing Blow"),
            actions.MoveAction(trainer=trainer_b_id, move_name="Tap"),
        ]
    )

    assert not any(event.kind == "stat_change" for event in turn_events)
    assert any(isinstance(event, events.FaintEvent) and event.target == "Defender" for event in turn_events)
    assert defender.stat_stages.defense == 0

    messages = battle_read.events_to_messages(
        turn_events,
        hero_name="Attacker",
        wild_name="Defender",
    )
    assert not any("defense" in message.lower() for message in messages)
