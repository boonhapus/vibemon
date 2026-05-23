from collections.abc import AsyncGenerator
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models


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


async def _seed_vibemon(sess: AsyncSession, *, trainer_id: uuid.UUID | None = None) -> uuid.UUID:
    seed = models.BirthSeed(timestamp=dt.datetime(2026, 5, 18, tzinfo=dt.UTC), geo_coords=[0.0, 0.0])
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    row = models.Vibemon(
        id=uuid.uuid7(),
        nickname="x",
        xp=0,
        level=1,
        evo_stage=0,
        lifecycle="christened",
        disposition=None,
        team_slot=None,
        trainer_id=trainer_id,
        birth_snapshot=snapshot,
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
    )
    row.identity = models.Identity(
        name="test",
        visual_notes=None,
        provider_visual_notes=None,
        elements=["fire"],
        base_hp=1,
        base_attack=1,
        base_defense=1,
        base_sp_attack=1,
        base_sp_defense=1,
        base_speed=1,
        evo_seed=0,
        is_radiant=False,
        generation=0,
        generated_at=dt.datetime(2026, 5, 18, tzinfo=dt.UTC),
    )
    sess.add(row)
    await sess.flush()
    return row.id


@pytest.mark.asyncio
async def test_disposition_invariant_rejects_owned_without_trainer(sess: AsyncSession) -> None:
    vibemon_id = await _seed_vibemon(sess)
    row = await sess.get(models.Vibemon, vibemon_id)
    assert row is not None
    row.disposition = "owned"
    row.team_slot = 0
    row.trainer_id = None
    with pytest.raises(IntegrityError):
        await sess.flush()


@pytest.mark.asyncio
async def test_disposition_invariant_rejects_null_disposition_with_owner(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    await sess.flush()
    vibemon_id = await _seed_vibemon(sess)
    row = await sess.get(models.Vibemon, vibemon_id)
    assert row is not None
    row.disposition = None
    row.team_slot = 0
    row.trainer_id = trainer_id
    with pytest.raises(IntegrityError):
        await sess.flush()


@pytest.mark.asyncio
async def test_candidate_review_invariant_rejects_resolved_pending(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"t-{trainer_id}"))
    vibemon_id = await _seed_vibemon(sess)
    review = models.CandidateReview(
        vibemon_id=vibemon_id,
        trainer_id=trainer_id,
        status="pending",
        shown_at=dt.datetime(2026, 5, 18, tzinfo=dt.UTC),
        timeout_at=dt.datetime(2026, 5, 19, tzinfo=dt.UTC),
        resolved_at=dt.datetime(2026, 5, 18, tzinfo=dt.UTC),
        resolution="timed_out",
    )
    sess.add(review)
    with pytest.raises(IntegrityError):
        await sess.flush()
