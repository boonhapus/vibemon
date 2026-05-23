from collections.abc import AsyncIterator
from typing import ClassVar
import datetime as dt
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import pytest

from app import models, schema, types
from app.plugins.provider import VibeProvider
from app.services import vibemon_service

NOW = dt.datetime(2026, 5, 17, 12, 0, tzinfo=dt.UTC)


class FakeProvider(VibeProvider):
    name = "fake"
    exposed_elements: ClassVar = [(types.VibemonTypeT.FIRE, "test heat")]

    async def fetch(self, seed: schema.BirthSeed) -> dict[str, object]:
        return {"ok": True}

    async def synthesize(self, seed: schema.BirthSeed, payload: dict[str, object]) -> schema.Affinity:
        return schema.Affinity(
            identity=schema.Identity(
                name="emberling",
                elements=(types.VibemonTypeT.FIRE,),
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_sp_attack=70,
                base_sp_defense=70,
                base_speed=70,
            ),
            provider_id=self.name,
            intensity=1.0,
            moves=self.moves(),
        )

    def moves(self) -> tuple[schema.Move, ...]:
        return (
            schema.Move(
                id="fake.m1",
                name="m1",
                flavor_text="f",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.PHYSICAL,
                power=40,
            ),
            schema.Move(
                id="fake.m2",
                name="m2",
                flavor_text="f",
                type=types.VibemonTypeT.FIRE,
                category=types.MoveCategoryT.PHYSICAL,
                power=40,
            ),
        )

    async def teardown(self) -> None:
        pass


async def fake_christen(vibemon: schema.Vibemon) -> schema.Vibemon:
    vibemon.lifecycle = types.VibemonLifecycleT.CHRISTENED
    return vibemon


@pytest.fixture
async def sess() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


def _service(now: dt.datetime = NOW) -> vibemon_service.VibemonService:
    return vibemon_service.VibemonService(
        clock=lambda: now,
        rng=random.Random(1),
        christen_step=fake_christen,
    )


async def _trainer(sess: AsyncSession) -> uuid.UUID:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"trainer-{trainer_id}"))
    await sess.flush()
    return trainer_id


@pytest.mark.asyncio
async def test_stale_hold_does_not_block_generation(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    # Simulate a stale hold from 1 hour ago
    stale_time = NOW - dt.timedelta(hours=1)
    row = models.GenerationCreditDay(
        trainer_id=trainer_id,
        credit_date=stale_time.date(),
        credits_consumed=0,
        active_hold_id=uuid.uuid7(),
        hold_started_at=stale_time,
    )
    sess.add(row)
    await sess.commit()

    # This should now succeed because of auto-expiry
    result = await _service().generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=schema.BirthSeed(timestamp=NOW, geo_coords=(0, 0), providers=[FakeProvider()]),
    )
    assert result is not None

    await sess.refresh(row)
    assert row.credits_consumed == 1
    assert row.active_hold_id is None


@pytest.mark.asyncio
async def test_resolve_stale_holds_clears_expired_holds(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    stale_time = NOW - dt.timedelta(minutes=30)
    row = models.GenerationCreditDay(
        trainer_id=trainer_id,
        credit_date=stale_time.date(),
        credits_consumed=0,
        active_hold_id=uuid.uuid7(),
        hold_started_at=stale_time,
    )
    sess.add(row)
    await sess.commit()

    service = _service()
    count = await service.resolve_stale_holds(sess, timeout=dt.timedelta(minutes=10))
    assert count == 1
    await sess.refresh(row)
    assert row.active_hold_id is None
    assert row.hold_started_at is None
