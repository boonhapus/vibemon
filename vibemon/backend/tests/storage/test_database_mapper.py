import datetime as dt
import uuid

import pytest

from app.domains.move.entity import EffectGroup, Move, MoveBehavior, StatusInflict
from app.domains.move.types import MoveCategoryT, MoveTargetT, StatusConditionT, VibemonTypeT
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT
from app.storage.database import mapper, models


def _move_row(
    *,
    content_id: str,
    name: str,
    type_: VibemonTypeT = VibemonTypeT.FIRE,
) -> models.Move:
    return models.Move(
        id=uuid.uuid7(),
        content_id=content_id,
        name=name,
        flavor_text="A focused test move.",
        type=type_.value,
        category=MoveCategoryT.SPECIAL.value,
        power=40,
        accuracy=1.0,
        pp=20,
        priority=0,
        target=MoveTargetT.SINGLE.value,
        level_requirement=1,
        effects=[
            EffectGroup(
                chance=0.25,
                effects=(StatusInflict(status=StatusConditionT.BURN),),
            ).model_dump(mode="json")
        ],
        behavior=MoveBehavior().model_dump(mode="json"),
    )


def _identity(generated_at: dt.datetime) -> Identity:
    return Identity(
        name="Cindlet",
        visual_notes="bright ember crest",
        provider_visual_notes="clear midday sun",
        elements=(VibemonTypeT.FIRE, VibemonTypeT.FLYING),
        base=BaseStats(
            hp=61,
            attack=72,
            defense=55,
            sp_attack=88,
            sp_defense=64,
            speed=91,
        ),
        evo_seed=EvolutionStageT.STAGE_2,
        is_radiant=True,
        generation=2,
        generated_at=generated_at,
    )


@pytest.mark.asyncio
async def test_vibemon_from_row_maps_identity_moves_and_assets() -> None:
    vibemon_id = uuid.uuid7()
    generated_at = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    trainer_id = uuid.uuid7()
    ember = _move_row(content_id="test.ember", name="Ember")
    gust = _move_row(content_id="test.gust", name="Gust", type_=VibemonTypeT.FLYING)
    row = models.Vibemon(
        id=vibemon_id,
        nickname="Blaze",
        xp=125,
        level=8,
        evo_stage=EvolutionStageT.STAGE_2.value,
        lifecycle=VibemonLifecycleT.MANIFESTED.value,
        disposition="owned",
        crew_slot=1,
        trainer_id=trainer_id,
        birth_snapshot_id=uuid.uuid7(),
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
    )
    row.identity = models.Identity(
        id=uuid.uuid7(),
        vibemon_id=vibemon_id,
        name="Cindlet",
        visual_notes="bright ember crest",
        provider_visual_notes="clear midday sun",
        elements=[VibemonTypeT.FIRE.value, VibemonTypeT.FLYING.value],
        base_hp=61,
        base_attack=72,
        base_defense=55,
        base_sp_attack=88,
        base_sp_defense=64,
        base_speed=91,
        evo_seed=EvolutionStageT.STAGE_2.value,
        is_radiant=True,
        generation=2,
        generated_at=generated_at,
    )
    row.moves = [
        models.VibemonMove(
            vibemon_id=vibemon_id,
            move_content_id=gust.content_id,
            active_slot=1,
            move=gust,
        ),
        models.VibemonMove(
            vibemon_id=vibemon_id,
            move_content_id=ember.content_id,
            active_slot=0,
            move=ember,
        ),
    ]
    row.assets = [
        models.VibemonAsset(
            id=uuid.uuid7(),
            vibemon_id=vibemon_id,
            kind=AssetKind.REFERENCE.value,
            selected_revision=1,
            max_revision=1,
            object_key="vibemon/test/reference.png",
            content_type="image/png",
            byte_size=1234,
            sha256="abc123",
            created_at=generated_at,
            updated_at=generated_at,
        )
    ]

    vibemon = await mapper.vibemon_from_row(row)

    assert vibemon.id == vibemon_id
    assert vibemon.nickname == "Blaze"
    assert vibemon.trainer_id == trainer_id
    assert vibemon.crew_slot == 1
    assert vibemon.lifecycle is VibemonLifecycleT.MANIFESTED
    assert vibemon.identity == _identity(generated_at)
    assert [move.id for move in vibemon.moves] == ["test.ember", "test.gust"]
    assert vibemon.moves[0].effects == (
        EffectGroup(chance=0.25, effects=(StatusInflict(status=StatusConditionT.BURN),)),
    )
    assert vibemon.moves[0].behavior == MoveBehavior()
    assert vibemon.aesthetic is not None
    assert vibemon.aesthetic.assets[AssetKind.REFERENCE].key == "vibemon/test/reference.png"


def test_identity_row_copies_domain_identity_values() -> None:
    generated_at = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    vibemon = Vibemon(
        identity=_identity(generated_at),
        moves=(
            Move(
                id="test.ember",
                name="Ember",
                flavor_text="A focused test move.",
                type=VibemonTypeT.FIRE,
                category=MoveCategoryT.SPECIAL,
                power=40,
                target=MoveTargetT.SINGLE,
            ),
        ),
    )

    row = mapper.identity_row(vibemon)

    assert row.name == "Cindlet"
    assert row.elements == [VibemonTypeT.FIRE.value, VibemonTypeT.FLYING.value]
    assert row.base_sp_attack == 88
    assert row.evo_seed == EvolutionStageT.STAGE_2.value
    assert row.is_radiant is True
    assert row.generated_at == generated_at


def test_apply_vibemon_to_row_updates_mutable_projection_fields() -> None:
    generated_at = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    row = models.Vibemon(
        id=uuid.uuid7(),
        nickname=None,
        xp=0,
        level=1,
        evo_stage=EvolutionStageT.BASE.value,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=None,
        crew_slot=None,
        trainer_id=None,
        birth_snapshot_id=uuid.uuid7(),
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
    )
    row.identity = models.Identity(
        id=uuid.uuid7(),
        vibemon_id=row.id,
        name="Oldname",
        visual_notes=None,
        provider_visual_notes=None,
        elements=[VibemonTypeT.FIRE.value],
        base_hp=50,
        base_attack=50,
        base_defense=50,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=50,
        evo_seed=EvolutionStageT.BASE.value,
        is_radiant=False,
        generation=0,
        generated_at=generated_at,
    )
    vibemon = Vibemon(
        id=row.id,
        nickname="Newname",
        identity=_identity(generated_at),
        level=9,
        xp=321,
        evo_stage=EvolutionStageT.STAGE_2,
        lifecycle=VibemonLifecycleT.CHRISTENED,
    )

    mapper.apply_vibemon_to_row(row, vibemon)

    assert row.nickname == "Newname"
    assert row.xp == 321
    assert row.level == 9
    assert row.evo_stage == EvolutionStageT.STAGE_2.value
    assert row.lifecycle == VibemonLifecycleT.CHRISTENED.value
    assert row.identity.name == "Cindlet"


def test_apply_adopted_vibemon_to_row_sets_owned_disposition_fields() -> None:
    generated_at = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    trainer_id = uuid.uuid7()
    row = models.Vibemon(
        id=uuid.uuid7(),
        nickname=None,
        xp=0,
        level=1,
        evo_stage=EvolutionStageT.BASE.value,
        lifecycle=VibemonLifecycleT.CHRISTENED.value,
        disposition="wild",
        crew_slot=None,
        trainer_id=None,
        birth_snapshot_id=uuid.uuid7(),
        wild_entered_at=generated_at,
        last_encountered_at=generated_at,
        expired_at=None,
    )
    row.identity = models.Identity(
        id=uuid.uuid7(),
        vibemon_id=row.id,
        name="Oldname",
        visual_notes=None,
        provider_visual_notes=None,
        elements=[VibemonTypeT.FIRE.value],
        base_hp=50,
        base_attack=50,
        base_defense=50,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=50,
        evo_seed=EvolutionStageT.BASE.value,
        is_radiant=False,
        generation=0,
        generated_at=generated_at,
    )
    vibemon = Vibemon(
        id=row.id,
        nickname="Sparky",
        identity=_identity(generated_at),
        lifecycle=VibemonLifecycleT.CHRISTENED,
    )

    mapper.apply_adopted_vibemon_to_row(row, vibemon, trainer_id=trainer_id, crew_slot=3)

    assert row.nickname == "Sparky"
    assert row.trainer_id == trainer_id
    assert row.crew_slot == 3
    assert row.disposition == "owned"
    assert row.wild_entered_at is None
    assert row.last_encountered_at is None
