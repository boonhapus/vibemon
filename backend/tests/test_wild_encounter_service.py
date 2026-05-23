from collections.abc import AsyncGenerator
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy as sa

from app import models, types
from app.services.wild_encounter import WildEncounterService
from app.services.wild_pool import WildPoolService

NOW = dt.datetime(2026, 5, 17, 12, 0, tzinfo=dt.UTC)


@pytest.fixture
async def sess() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            yield session
    finally:
        await engine.dispose()


async def _insert_wild(
    sess: AsyncSession,
    *,
    lat: float,
    lon: float,
    level: int = 15,
    base_stat: int = 70,
) -> uuid.UUID:
    seed = models.BirthSeed(timestamp=NOW, geo_coords=[lat, lon])
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    vibemon_id = uuid.uuid7()
    vibemon = models.Vibemon(
        id=vibemon_id,
        nickname="wildling",
        level=level,
        evo_stage=1,
        lifecycle=types.VibemonLifecycleT.CHRISTENED.value,
        disposition=types.VibemonDispositionT.WILD.value,
        team_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=NOW,
        last_encountered_at=NOW,
        expired_at=None,
        identity=models.Identity(
            name="wildling",
            visual_notes=None,
            provider_visual_notes=None,
            elements=[types.VibemonTypeT.NORMAL.value],
            base_hp=base_stat,
            base_attack=base_stat,
            base_defense=base_stat,
            base_sp_attack=base_stat,
            base_sp_defense=base_stat,
            base_speed=base_stat,
            evo_seed=1,
            is_radiant=False,
            generation=0,
            generated_at=NOW,
        ),
    )
    sess.add(vibemon)
    await sess.flush()
    return vibemon_id


@pytest.mark.asyncio
async def test_pick_encounter_tops_up_supply_before_selecting(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    created: list[uuid.UUID] = []

    async def fake_supply(inner_sess: AsyncSession, lat: float, lon: float) -> uuid.UUID:
        vibemon_id = await _insert_wild(inner_sess, lat=lat, lon=lon, level=10)
        created.append(vibemon_id)
        return vibemon_id

    service = WildEncounterService(
        wild_pool=WildPoolService(),
        clock=lambda: NOW,
        supply_generator=fake_supply,
    )
    selection = await service.pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.0,
        longitude=-87.0,
        party_strength=500.0,
        desired_supply=3,
    )
    assert selection is not None
    assert len(created) == 3


@pytest.mark.asyncio
async def test_pick_encounter_prefers_bucket_priority_order(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    service = WildEncounterService(wild_pool=WildPoolService(), clock=lambda: NOW)
    center_id = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    await _insert_wild(sess, lat=0.0, lon=0.0, level=12)

    selection = await service.pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.0,
        longitude=-87.0,
        party_strength=400.0,
        desired_supply=1,
    )
    assert selection is not None
    assert selection.vibemon_id == center_id


@pytest.mark.asyncio
async def test_pick_encounter_applies_adjustment_multiplier(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    blocked = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    open_id = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    sess.add(
        models.EncounterAdjustment(
            trainer_id=trainer_id,
            vibemon_id=blocked,
            source="test",
            initial_multiplier=0.0,
            starts_at=NOW,
            ends_at=NOW + dt.timedelta(days=1),
        )
    )
    await sess.flush()
    service = WildEncounterService(wild_pool=WildPoolService(), clock=lambda: NOW)

    selection = await service.pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.0,
        longitude=-87.0,
        party_strength=400.0,
        desired_supply=2,
    )
    assert selection is not None
    assert selection.vibemon_id == open_id


@pytest.mark.asyncio
async def test_pick_encounter_revalidates_before_return(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    first = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    second = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    sess.add(
        models.CandidateReview(
            vibemon_id=first,
            trainer_id=trainer_id,
            status=types.CandidateReviewStatusT.PENDING.value,
            shown_at=NOW,
            timeout_at=NOW + dt.timedelta(hours=24),
            resolved_at=None,
            resolution=None,
        )
    )
    await sess.flush()

    service = WildEncounterService(wild_pool=WildPoolService(), clock=lambda: NOW)
    selection = await service.pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.0,
        longitude=-87.0,
        party_strength=400.0,
        desired_supply=2,
    )
    assert selection is not None
    assert selection.vibemon_id == second
    count = (
        await sess.execute(
            sa.select(sa.func.count()).select_from(models.Vibemon).where(models.Vibemon.disposition == "wild")
        )
    ).scalar_one()
    assert count >= 1


@pytest.mark.asyncio
async def test_pick_encounter_calls_reveal_hook_for_selected_vibemon(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    chosen = await _insert_wild(sess, lat=41.0, lon=-87.0, level=12)
    seen: list[uuid.UUID] = []

    async def reveal_hook(_sess: AsyncSession, vibemon_id: uuid.UUID) -> None:
        seen.append(vibemon_id)

    service = WildEncounterService(
        wild_pool=WildPoolService(),
        clock=lambda: NOW,
        reveal_hook=reveal_hook,
    )
    selection = await service.pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.0,
        longitude=-87.0,
        party_strength=400.0,
        desired_supply=1,
    )
    assert selection is not None
    assert selection.vibemon_id == chosen
    assert seen == [chosen]
