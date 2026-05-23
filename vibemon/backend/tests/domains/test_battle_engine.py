from __future__ import annotations

import random
import uuid

import pytest

from app.domains.battle import actions, engine, entity, events
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, VibemonTypeT
from app.domains.vibemon.identity import Identity


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
            base_attack=190,
            base_speed=200,
        ),
        moves=(strike,),
        level=50,
    )
    defender = entity.BattleVibemon(
        identity=Identity(
            name="Defender",
            elements=(VibemonTypeT.NORMAL,),
            base_hp=1,
            base_defense=5,
            base_speed=5,
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
            identity=Identity(name=name, elements=(VibemonTypeT.NORMAL,)),
            moves=(move,),
        )

    battle_engine = engine.GameEngine(
        entity.BattleTrainer(id=trainer_a_id, username="a", team=[vibemon("A")]),
        entity.BattleTrainer(id=trainer_b_id, username="b", team=[vibemon("B")]),
    )

    with pytest.raises(ValueError, match="exactly one action"):
        battle_engine.submit_actions([actions.MoveAction(trainer=trainer_a_id, move_name="Tap")])
