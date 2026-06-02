import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import EvolutionStageT, VibemonLifecycleT
from app.providers.base import VibeProvider
from app.providers.climate.schema import ClimatePayload
from app.storage.database import models
from app.workflows.rebalance_vibemon import rebalance_existing_vibemons
from tests.conftest import TEST_TRAINER_ID

_CLIMATE_PAYLOAD = ClimatePayload(
    start_date="2026-05-01",
    end_date="2026-05-19",
    weather_augmented={"weather": "clear"},
)


class FakeClimateProvider(VibeProvider[ClimatePayload]):
    name = "climate"
    payload_type = ClimatePayload

    async def fetch(self, seed: BirthSeed, *, secrets: object | None = None) -> ClimatePayload:
        return _CLIMATE_PAYLOAD

    async def synthesize(self, seed: BirthSeed, payload: ClimatePayload) -> Affinity:
        return Affinity(
            identity=Identity(
                name="Ignored",
                elements=(VibemonTypeT.WATER,),
                base=BaseStats(hp=92, attack=64, defense=81, sp_attack=88, sp_defense=93, speed=57),
            ),
            intensity=1.0,
            provider_id=self.name,
            element_rankings={VibemonTypeT.WATER: 1.0},
            moves=(
                Move(
                    id="climate.wave_test",
                    name="Wave Test",
                    flavor_text="A controlled test wave.",
                    type=VibemonTypeT.WATER,
                    category=MoveCategoryT.SPECIAL,
                    power=40,
                    accuracy=1.0,
                    pp=20,
                    target=MoveTargetT.SINGLE,
                ),
                Move(
                    id="climate.splash_test",
                    name="Splash Test",
                    flavor_text="A precise test splash.",
                    type=VibemonTypeT.WATER,
                    category=MoveCategoryT.PHYSICAL,
                    power=35,
                    accuracy=1.0,
                    pp=25,
                    target=MoveTargetT.SINGLE,
                ),
            ),
        )


async def _add_stale_vibemon(sess: AsyncSession, *, vibemon_id: uuid.UUID, now: dt.datetime) -> None:
    old_move = models.Move(
        content_id="climate.old_test",
        name="Old Test",
        flavor_text="An outdated test move.",
        type=VibemonTypeT.FIRE.value,
        category=MoveCategoryT.PHYSICAL.value,
        power=20,
        accuracy=1.0,
        pp=30,
        priority=0,
        target=MoveTargetT.SINGLE.value,
        level_requirement=1,
        effects=[],
        behavior={},
    )
    seed = models.BirthSeed(timestamp=now, geo_coords=[41.8781, -87.6298], trainer_id=TEST_TRAINER_ID)
    snapshot = models.BirthSnapshot(
        birth_seed=seed,
        provider_payloads={"climate": _CLIMATE_PAYLOAD.model_dump(mode="json")},
    )
    row = models.Vibemon(
        id=vibemon_id,
        nickname="Stale",
        xp=12,
        level=4,
        evo_stage=EvolutionStageT.BASE.value,
        lifecycle=VibemonLifecycleT.CHRISTENED.value,
        disposition=VibemonDispositionT.WILD.value,
        team_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=now,
        last_encountered_at=now,
        expired_at=None,
    )
    row.identity = models.Identity(
        name="Oldling",
        visual_notes="original idea",
        provider_visual_notes="old dry weather",
        elements=[VibemonTypeT.FIRE.value],
        base_hp=50,
        base_attack=50,
        base_defense=50,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=50,
        evo_seed=EvolutionStageT.BASE.value,
        is_radiant=False,
        generation=3,
        generated_at=now,
    )
    row.moves = [models.VibemonMove(move=old_move, move_content_id=old_move.content_id, active_slot=0)]
    sess.add(row)
    await sess.flush()


@pytest.mark.asyncio
async def test_rebalance_existing_vibemons_previews_without_mutating(sess: AsyncSession, test_trainer: object) -> None:
    vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    await _add_stale_vibemon(sess, vibemon_id=vibemon_id, now=now)

    results = await rebalance_existing_vibemons(
        sess,
        vibemon_id=vibemon_id,
        dry_run=True,
        providers=[FakeClimateProvider()],
    )

    row = (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(
                sa.orm.selectinload(models.Vibemon.identity),
                sa.orm.selectinload(models.Vibemon.moves),
            )
            .where(models.Vibemon.id == vibemon_id)
        )
    ).scalar_one()
    assert len(results) == 1
    assert results[0].changed is True
    assert results[0].before_elements == (VibemonTypeT.FIRE,)
    assert results[0].after_elements == (VibemonTypeT.WATER,)
    assert row.identity.elements == [VibemonTypeT.FIRE.value]
    assert [move.move_content_id for move in row.moves] == ["climate.old_test"]


@pytest.mark.asyncio
async def test_rebalance_existing_vibemons_updates_identity_and_active_moves(
    sess: AsyncSession, test_trainer: object
) -> None:
    vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    await _add_stale_vibemon(sess, vibemon_id=vibemon_id, now=now)

    results = await rebalance_existing_vibemons(
        sess,
        vibemon_id=vibemon_id,
        dry_run=False,
        providers=[FakeClimateProvider()],
    )

    row = (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(
                sa.orm.selectinload(models.Vibemon.identity),
                sa.orm.selectinload(models.Vibemon.moves),
            )
            .where(models.Vibemon.id == vibemon_id)
        )
    ).scalar_one()
    history_count = (await sess.execute(sa.select(sa.func.count()).select_from(models.VibemonHistory))).scalar_one()
    assert results[0].changed is True
    assert row.nickname == "Stale"
    assert row.lifecycle == VibemonLifecycleT.CHRISTENED.value
    assert row.disposition == VibemonDispositionT.WILD.value
    assert row.identity.name == "Oldling"
    assert row.identity.visual_notes == "original idea"
    assert row.identity.elements == [VibemonTypeT.WATER.value]
    assert row.identity.generation == 3
    assert row.identity.generated_at == now
    assert sorted(move.move_content_id for move in row.moves) == ["climate.splash_test", "climate.wave_test"]
    assert history_count == 0
