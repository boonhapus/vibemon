"""Workflow tests for interactive battle sessions."""

import datetime as dt
import uuid

import pytest

from app.domains.move.entity import EffectGroup, Move, MoveBehavior
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.types import VibemonLifecycleT
from app.http.battle_read import battle_state_read
from app.storage.database import models
from app.workflows.battle_play import BattleSessionRegistry, start_wild_battle, submit_player_turn
from tests.conftest import TEST_TRAINER_ID


def _move_row(*, content_id: str, name: str, power: int = 120) -> models.Move:
    return models.Move(
        id=uuid.uuid7(),
        content_id=content_id,
        name=name,
        flavor_text="Test move.",
        type=VibemonTypeT.NORMAL.value,
        category=MoveCategoryT.PHYSICAL.value,
        power=power,
        accuracy=1.0,
        pp=20,
        priority=0,
        target=MoveTargetT.SINGLE.value,
        level_requirement=1,
        effects=[EffectGroup(effects=(), trigger="on_hit", chance=1.0).model_dump(mode="json")],
        behavior=MoveBehavior().model_dump(mode="json"),
    )


@pytest.mark.asyncio
async def test_start_wild_battle_and_turn(sess, test_trainer) -> None:
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    hero_id = uuid.uuid7()
    wild_id = uuid.uuid7()
    trainer_row = await sess.get(models.Trainer, TEST_TRAINER_ID)
    assert trainer_row is not None

    seed = models.BirthSeed(timestamp=now, geo_coords=[41.0, -87.0], trainer_id=TEST_TRAINER_ID)
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})

    hero = models.Vibemon(
        id=hero_id,
        nickname=None,
        xp=0,
        level=12,
        evo_stage=1,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.OWNED.value,
        crew_slot=0,
        trainer_id=TEST_TRAINER_ID,
        birth_snapshot=snapshot,
    )
    hero.identity = models.Identity(
        name="Hero",
        visual_notes=None,
        provider_visual_notes=None,
        elements=["normal"],
        base_hp=80,
        base_attack=90,
        base_defense=70,
        base_sp_attack=70,
        base_sp_defense=70,
        base_speed=90,
        evo_seed=1,
        is_radiant=False,
        generated_at=now,
    )
    strike = _move_row(content_id="test.strike", name="Strike")
    hero.moves = [
        models.VibemonMove(
            vibemon_id=hero_id,
            move_content_id=strike.content_id,
            active_slot=0,
            move=strike,
        )
    ]

    wild = models.Vibemon(
        id=wild_id,
        nickname=None,
        xp=0,
        level=3,
        evo_stage=1,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.WILD.value,
        crew_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=now,
    )
    wild.identity = models.Identity(
        name="Fodder",
        visual_notes=None,
        provider_visual_notes=None,
        elements=["normal"],
        base_hp=20,
        base_attack=10,
        base_defense=20,
        base_sp_attack=10,
        base_sp_defense=20,
        base_speed=10,
        evo_seed=1,
        is_radiant=False,
        generated_at=now,
    )
    tap = _move_row(content_id="test.tap", name="Tap", power=1)
    wild.moves = [
        models.VibemonMove(
            vibemon_id=wild_id,
            move_content_id=tap.content_id,
            active_slot=0,
            move=tap,
        )
    ]

    sess.add(hero)
    sess.add(wild)
    await sess.flush()

    registry = BattleSessionRegistry()
    session = await start_wild_battle(
        sess,
        registry=registry,
        trainer_id=TEST_TRAINER_ID,
        trainer_name=trainer_row.username,
        hero_vibemon_id=hero_id,
        wild_vibemon_id=wild_id,
    )
    state = battle_state_read(
        session,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=wild_id,
    )
    assert state.player.name == "Hero"
    assert state.opponent.name == "Fodder"

    events = submit_player_turn(session, move_name="Strike")
    assert events
    assert battle_state_read(
        session,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=wild_id,
    ).concluded is True
