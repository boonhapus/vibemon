"""Tests for Vibemon XP curve, milestones, and battle progression."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from app.domains.battle import entity, events
from app.domains.move.entity import EffectGroup, Move, MoveBehavior
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.progression import engine as progression_engine
from app.domains.vibemon.progression import formulas
from app.domains.vibemon.progression.types import GrowthGroupT
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT
from app.storage.database import models
from app.workflows.battle_play import (
    BattleSessionRegistry,
    finish_battle,
    start_wild_battle,
    submit_player_turn,
)
from tests.conftest import TEST_TRAINER_ID


def _move(*, content_id: str, name: str, power: int = 120, level_requirement: int = 1) -> Move:
    return Move(
        id=content_id,
        name=name,
        flavor_text="Test move.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=power,
        accuracy=1.0,
        pp=20,
        priority=0,
        target=MoveTargetT.SINGLE,
        level_requirement=level_requirement,
        effects=[EffectGroup(effects=(), trigger="on_hit", chance=1.0)],
        behavior=MoveBehavior(),
    )


def _vibemon(
    *,
    name: str = "Testmon",
    level: int = 1,
    xp: int = 0,
    growth_rate: GrowthGroupT = GrowthGroupT.MEDIUM,
    evo_seed: EvolutionStageT = EvolutionStageT.STAGE_3,
    evo_stage: EvolutionStageT = EvolutionStageT.BASE,
    trainer_id: uuid.UUID | None = None,
) -> Vibemon:
    return Vibemon(
        id=uuid.uuid7(),
        identity=Identity(
            name=name,
            elements=(VibemonTypeT.NORMAL,),
            base=BaseStats(hp=70, attack=70, defense=70, sp_attack=70, sp_defense=70, speed=70),
            evo_seed=evo_seed,
        ),
        moves=(_move(content_id="test.strike", name="Strike"),),
        level=level,
        xp=xp,
        growth_rate=growth_rate,
        evo_stage=evo_stage,
        trainer_id=trainer_id,
    )


def test_xp_curve_is_cubic_by_growth_group() -> None:
    assert formulas.xp_to_reach_level(10, growth_rate=GrowthGroupT.FAST) == 4_000
    assert formulas.xp_to_reach_level(10, growth_rate=GrowthGroupT.MEDIUM) == 5_000
    assert formulas.xp_to_reach_level(10, growth_rate=GrowthGroupT.SLOW) == 6_000


def test_xp_bar_helpers_use_within_level_bounds() -> None:
    level = 8
    growth = GrowthGroupT.MEDIUM
    floor = formulas.xp_to_reach_level(level, growth_rate=growth)
    ceiling = formulas.xp_to_reach_level(level + 1, growth_rate=growth)
    mid_xp = floor + (ceiling - floor) // 2

    assert formulas.xp_to_next_level(level=level, xp=mid_xp, growth_rate=growth) == ceiling - mid_xp
    ratio = formulas.xp_bar_ratio(level=level, xp=mid_xp, growth_rate=growth)
    assert 0.45 <= ratio <= 0.55
    assert formulas.xp_bar_ratio(level=level, xp=floor, growth_rate=growth) == 0.0


def test_level_from_total_xp_respects_growth_rate() -> None:
    assert formulas.level_from_total_xp(4_000, growth_rate=GrowthGroupT.FAST) == 10
    assert formulas.level_from_total_xp(4_000, growth_rate=GrowthGroupT.MEDIUM) == 9


def test_stage_at_level_uses_growth_gated_milestones() -> None:
    assert (
        formulas.stage_at_level(
            level=15,
            growth_rate=GrowthGroupT.MEDIUM,
            evo_seed=EvolutionStageT.STAGE_3,
        )
        is EvolutionStageT.BASE
    )
    assert (
        formulas.stage_at_level(
            level=16,
            growth_rate=GrowthGroupT.MEDIUM,
            evo_seed=EvolutionStageT.STAGE_3,
        )
        is EvolutionStageT.STAGE_2
    )
    assert (
        formulas.stage_at_level(
            level=36,
            growth_rate=GrowthGroupT.MEDIUM,
            evo_seed=EvolutionStageT.STAGE_3,
        )
        is EvolutionStageT.STAGE_3
    )


def test_pending_evolution_stage_derived_without_storage() -> None:
    pending = formulas.pending_evolution_stage(
        level=18,
        growth_rate=GrowthGroupT.MEDIUM,
        evo_seed=EvolutionStageT.STAGE_3,
        current_stage=EvolutionStageT.BASE,
    )
    assert pending is EvolutionStageT.STAGE_2


def test_accumulate_battle_xp_awards_killer_and_participation() -> None:
    hero = _vibemon(level=12, trainer_id=TEST_TRAINER_ID, name="Hero")
    wild = _vibemon(level=3, name="Fodder")
    battle = entity.Battle(
        trainer_a=entity.BattleTrainer(id=TEST_TRAINER_ID, username="Hero", crew=[hero]),
        trainer_b=entity.BattleTrainer(id=uuid.uuid7(), username="Wild", crew=[wild]),
    )
    battle.turn_history.append(
        entity.TurnRecord(
            turn_number=1,
            events=[events.FaintEvent(target=wild.name, source=hero.name)],
        )
    )
    awards = progression_engine.accumulate_battle_xp(battle)
    full_share = formulas.xp_award_for_faint(
        opponent_level=3,
        opponent_evo_seed=EvolutionStageT.STAGE_3,
        opponent_is_trainer_owned=False,
    )
    assert awards[hero.id] == full_share
    assert wild.id not in awards


def test_apply_evolution_rescales_base_stats() -> None:
    vibemon = _vibemon(evo_seed=EvolutionStageT.STAGE_3, evo_stage=EvolutionStageT.BASE)
    vibemon = vibemon.model_copy(
        update={
            "identity": vibemon.identity.model_copy(
                update={"base": BaseStats(hp=45, attack=45, defense=45, sp_attack=45, sp_defense=45, speed=45)}
            )
        }
    )
    before = vibemon.identity.bst
    evolved = progression_engine.apply_evolution(vibemon, to_stage=EvolutionStageT.STAGE_2)
    assert evolved.evo_stage is EvolutionStageT.STAGE_2
    assert evolved.identity.bst > before


@pytest.mark.asyncio
async def test_resolve_battle_progression_persists_xp_for_winner(sess: AsyncSession, test_trainer: uuid.UUID) -> None:
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
        growth_rate=GrowthGroupT.MEDIUM.value,
        evo_stage=EvolutionStageT.BASE.value,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.OWNED.value,
        crew_slot=0,
        trainer_id=TEST_TRAINER_ID,
        birth_snapshot=snapshot,
    )
    hero.identity = models.Identity(
        name="Hero",
        visual_notes=None,
        elements=["normal"],
        base_hp=80,
        base_attack=90,
        base_defense=70,
        base_sp_attack=70,
        base_sp_defense=70,
        base_speed=90,
        evo_seed=EvolutionStageT.BASE.value,
        is_radiant=False,
        generated_at=now,
    )
    strike = _move(content_id="test.strike", name="Strike")
    hero.moves = [
        models.VibemonMove(
            vibemon_id=hero_id,
            move_content_id=strike.id,
            active_slot=0,
            move=models.Move(
                id=uuid.uuid7(),
                content_id=strike.id,
                name=strike.name,
                flavor_text=strike.flavor_text,
                type=strike.type.value,
                category=strike.category.value,
                power=strike.power,
                accuracy=strike.accuracy,
                pp=strike.pp,
                priority=strike.priority,
                target=strike.target.value,
                level_requirement=strike.level_requirement,
                effects=[group.model_dump(mode="json") for group in strike.effects],
                behavior=strike.behavior.model_dump(mode="json"),
            ),
        )
    ]

    wild = models.Vibemon(
        id=wild_id,
        nickname=None,
        xp=0,
        level=3,
        growth_rate=GrowthGroupT.MEDIUM.value,
        evo_stage=EvolutionStageT.BASE.value,
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
        elements=["normal"],
        base_hp=20,
        base_attack=10,
        base_defense=20,
        base_sp_attack=10,
        base_sp_defense=20,
        base_speed=10,
        evo_seed=EvolutionStageT.BASE.value,
        is_radiant=False,
        generated_at=now,
    )
    tap = _move(content_id="test.tap", name="Tap", power=1)
    wild.moves = [
        models.VibemonMove(
            vibemon_id=wild_id,
            move_content_id=tap.id,
            active_slot=0,
            move=models.Move(
                id=uuid.uuid7(),
                content_id=tap.id,
                name=tap.name,
                flavor_text=tap.flavor_text,
                type=tap.type.value,
                category=tap.category.value,
                power=tap.power,
                accuracy=tap.accuracy,
                pp=tap.pp,
                priority=tap.priority,
                target=tap.target.value,
                level_requirement=tap.level_requirement,
                effects=[group.model_dump(mode="json") for group in tap.effects],
                behavior=tap.behavior.model_dump(mode="json"),
            ),
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
    submit_player_turn(session, move_name="Strike")

    result = await finish_battle(sess, session=session, now=now)
    hero_delta = next(delta for delta in result.deltas if delta.vibemon_id == hero_id)
    assert hero_delta.xp_award is not None
    assert hero_delta.xp_award.xp_gained > 0

    refreshed = await sess.get(models.Vibemon, hero_id)
    assert refreshed is not None
    assert refreshed.xp == hero_delta.xp_award.new_xp


def test_owned_offer_does_not_mutate_active_moves() -> None:
    battle_id = uuid.uuid7()
    starter = _move(content_id="test.strike", name="Strike")
    learnable = _move(content_id="test.learn", name="Learn", level_requirement=1)
    vibemon = _vibemon(level=1, xp=0, trainer_id=TEST_TRAINER_ID)
    pool = (starter, learnable)
    delta = progression_engine.resolve_progression_for_vibemon(
        vibemon,
        battle_id=battle_id,
        xp_gain=formulas.xp_to_reach_level(8, growth_rate=GrowthGroupT.MEDIUM),
        provider_moves=pool,
        universal_moves=(),
        learned_exclude_ids={starter.id},
        auto_evolve=False,
    )
    assert delta.xp_award is not None
    assert delta.xp_award.new_level > delta.xp_award.previous_level
    if delta.move_learn_offers:
        assert len(delta.vibemon.moves) == len(vibemon.moves)


def test_wild_offer_mutates_active_moves_on_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.domains.vibemon.progression import move_offers

    battle_id = uuid.uuid7()
    starter = _move(content_id="test.strike", name="Strike")
    learnable = _move(content_id="test.learn", name="Learn", level_requirement=1)
    vibemon = _vibemon(level=1, xp=0)
    monkeypatch.setattr(move_offers, "should_offer", lambda **_kwargs: True)
    pool = (starter, learnable)
    delta = progression_engine.resolve_progression_for_vibemon(
        vibemon,
        battle_id=battle_id,
        xp_gain=formulas.xp_to_reach_level(2, growth_rate=GrowthGroupT.MEDIUM),
        provider_moves=pool,
        universal_moves=(),
        learned_exclude_ids={starter.id},
        auto_evolve=True,
    )
    assert delta.move_learn_offers == ()
    assert len(delta.vibemon.moves) >= len(vibemon.moves)
