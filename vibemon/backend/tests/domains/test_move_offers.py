"""Tests for move learn offer eligibility and sampling."""

import random
import uuid

from app.domains.move.entity import EffectGroup, Move, MoveBehavior
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.progression import move_offers


def _move(*, content_id: str, level_requirement: int = 1, move_type: VibemonTypeT = VibemonTypeT.NORMAL) -> Move:
    return Move(
        id=content_id,
        name=content_id,
        flavor_text="Test.",
        type=move_type,
        category=MoveCategoryT.PHYSICAL,
        power=40,
        accuracy=1.0,
        pp=20,
        priority=0,
        target=MoveTargetT.SINGLE,
        level_requirement=level_requirement,
        effects=[EffectGroup(effects=(), trigger="on_hit", chance=1.0)],
        behavior=MoveBehavior(),
    )


def test_learned_and_forgotten_ids_excludes_birth_and_kept_not_rejected() -> None:
    events = (
        {"event_type": "move_learned", "payload": {"move_content_id": "birth.move", "source": "birth"}},
        {"event_type": "move_learned", "payload": {"move_content_id": "kept.move", "outcome": "kept"}},
        {"event_type": "move_learned", "payload": {"move_content_id": "rejected.move", "outcome": "rejected"}},
        {"event_type": "move_forgotten", "payload": {"move_content_id": "forgotten.move"}},
    )
    excluded = move_offers.learned_and_forgotten_ids(events)
    assert excluded == {"birth.move", "kept.move", "forgotten.move"}


def test_universal_fallback_only_when_provider_pool_thin() -> None:
    provider = (_move(content_id="provider.a"), _move(content_id="provider.b"))
    universal = (_move(content_id="universal.tackle"),)
    eligible = move_offers.eligible_with_universal_fallback(
        provider,
        universal,
        exclude_ids=set(),
        level=10,
        min_count=4,
    )
    assert {move.id for move in eligible} == {"provider.a", "provider.b", "universal.tackle"}

    full_provider = tuple(_move(content_id=f"provider.{index}") for index in range(5))
    eligible_full = move_offers.eligible_with_universal_fallback(
        full_provider,
        universal,
        exclude_ids=set(),
        level=10,
        min_count=4,
    )
    assert all(move.id.startswith("provider.") for move in eligible_full)
    assert len(eligible_full) == 5


def test_should_offer_guarantees_upgrade_on_large_jump() -> None:
    rng = random.Random(0)
    assert move_offers.should_offer(active_move_count=4, levels_crossed=7, rng=rng) is True


def test_should_offer_kit_building_is_probabilistic() -> None:
    hits = sum(
        1
        for seed in range(200)
        if move_offers.should_offer(
            active_move_count=2,
            levels_crossed=1,
            rng=random.Random(seed),
        )
    )
    assert 70 <= hits <= 130


def test_sample_move_options_returns_distinct_moves() -> None:
    pool = tuple(_move(content_id=f"move.{index}", level_requirement=index + 1) for index in range(8))
    rng = move_offers.offer_rng(battle_id=uuid.uuid7(), vibemon_id=uuid.uuid7())
    sample = move_offers.sample_move_options(pool, elements=(VibemonTypeT.NORMAL,), rng=rng)
    assert len(sample) == 4
    assert len({move.id for move in sample}) == 4


def test_sample_move_options_favors_matching_element_types() -> None:
    pool = (
        _move(content_id="fire.move", move_type=VibemonTypeT.FIRE, level_requirement=10),
        *(_move(content_id=f"other.{index}", move_type=VibemonTypeT.WATER, level_requirement=10) for index in range(7)),
    )
    fire_hits = 0
    for seed in range(200):
        rng = random.Random(seed)
        sample = move_offers.sample_move_options(
            pool,
            elements=(VibemonTypeT.FIRE,),
            element_rankings={VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.1},
            rng=rng,
        )
        if any(move.type == VibemonTypeT.FIRE for move in sample):
            fire_hits += 1
    assert fire_hits >= 170


def test_replacement_slot_picks_lowest_level_requirement() -> None:
    moves = (
        _move(content_id="test.high", level_requirement=20),
        _move(content_id="test.low", level_requirement=5),
        _move(content_id="test.mid", level_requirement=10),
    )
    assert move_offers.replacement_slot_index(moves) == 1


def test_sample_move_learn_offer_respects_level_cap() -> None:
    from app.domains.vibemon.entity import Vibemon
    from app.domains.vibemon.identity import BaseStats, Identity
    from app.domains.vibemon.progression import engine as progression_engine
    from app.domains.vibemon.types import EvolutionStageT

    vibemon = Vibemon(
        id=uuid.uuid7(),
        identity=Identity(
            name="Fliora",
            elements=(VibemonTypeT.FIRE, VibemonTypeT.GRASS),
            base=BaseStats(hp=70, attack=70, defense=70, sp_attack=70, sp_defense=70, speed=70),
            evo_seed=EvolutionStageT.STAGE_3,
        ),
        moves=(_move(content_id="test.strike"),),
        level=5,
    )
    provider = (
        _move(content_id="eligible.fire", level_requirement=5, move_type=VibemonTypeT.FIRE),
        _move(content_id="too_high.ice", level_requirement=18, move_type=VibemonTypeT.ICE),
    )
    offer = progression_engine.sample_move_learn_offer(
        vibemon,
        battle_id=uuid.uuid7(),
        provider_moves=provider,
        universal_moves=(),
        learned_exclude_ids=set(),
        rng=random.Random(0),
    )
    assert offer is not None
    assert all(move.level_requirement <= vibemon.level for move in offer.moves)
    assert "too_high.ice" not in {move.id for move in offer.moves}
    assert "eligible.fire" in {move.id for move in offer.moves}
