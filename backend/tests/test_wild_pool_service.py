from collections.abc import AsyncGenerator
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models, types
from app.services.wild_geography import geohash_bbox, geohash_encode, geohash_ring
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


async def _insert_wild(sess: AsyncSession, *, lat: float, lon: float) -> uuid.UUID:
    seed = models.BirthSeed(timestamp=NOW, geo_coords=[lat, lon])
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    vibemon_id = uuid.uuid7()
    vibemon = models.Vibemon(
        id=vibemon_id,
        nickname="wildling",
        level=10,
        evo_stage=1,
        lifecycle=types.VibemonLifecycleT.CHRISTENED.value,
        disposition=types.VibemonDispositionT.WILD.value,
        team_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=NOW,
        last_encountered_at=NOW,
        expired_at=None,
    )
    sess.add(vibemon)
    await sess.flush()
    return vibemon_id


@pytest.mark.asyncio
async def test_geohash_precision5_center_and_rings() -> None:
    center = geohash_encode(41.0, -87.0, precision=5)
    assert len(center) == 5
    assert len(geohash_ring(center, ring=1)) == 8
    assert len(geohash_ring(center, ring=2)) == 16


@pytest.mark.asyncio
async def test_list_eligible_wild_ids_excludes_expired_and_pending_review(sess: AsyncSession) -> None:
    service = WildPoolService()
    vibemon_id = await _insert_wild(sess, lat=41.0, lon=-87.0)
    expired_id = await _insert_wild(sess, lat=41.0, lon=-87.0)
    pending_id = await _insert_wild(sess, lat=41.0, lon=-87.0)

    expired = await sess.get(models.Vibemon, expired_id)
    assert expired is not None
    expired.expired_at = NOW
    expired.disposition = types.VibemonDispositionT.EXPIRED.value

    sess.add(
        models.CandidateReview(
            vibemon_id=pending_id,
            trainer_id=uuid.uuid7(),
            status=types.CandidateReviewStatusT.PENDING.value,
            shown_at=NOW,
            timeout_at=NOW + dt.timedelta(hours=24),
            resolved_at=None,
            resolution=None,
        )
    )
    await sess.flush()

    result = await service.list_eligible_wild_ids(sess, latitude=41.0, longitude=-87.0, limit=10)
    assert result == [vibemon_id]


@pytest.mark.asyncio
async def test_list_eligible_wild_ids_expands_local_then_ring1_then_ring2(sess: AsyncSession) -> None:
    service = WildPoolService()
    center = geohash_encode(41.0, -87.0, precision=5)
    center_box = geohash_bbox(center)
    center_lat = (center_box.lat_min + center_box.lat_max) / 2.0
    center_lon = (center_box.lon_min + center_box.lon_max) / 2.0
    await _insert_wild(sess, lat=center_lat, lon=center_lon)

    ring1_hash = next(iter(geohash_ring(center, ring=1)))
    ring1_box = geohash_bbox(ring1_hash)
    ring1_lat = (ring1_box.lat_min + ring1_box.lat_max) / 2.0
    ring1_lon = (ring1_box.lon_min + ring1_box.lon_max) / 2.0
    await _insert_wild(sess, lat=ring1_lat, lon=ring1_lon)

    ring2_hash = next(iter(geohash_ring(center, ring=2)))
    ring2_box = geohash_bbox(ring2_hash)
    ring2_lat = (ring2_box.lat_min + ring2_box.lat_max) / 2.0
    ring2_lon = (ring2_box.lon_min + ring2_box.lon_max) / 2.0
    await _insert_wild(sess, lat=ring2_lat, lon=ring2_lon)

    two = await service.list_eligible_wild_ids(sess, latitude=41.0, longitude=-87.0, limit=2)
    assert len(two) == 2
    all_three = await service.list_eligible_wild_ids(sess, latitude=41.0, longitude=-87.0, limit=3)
    assert len(all_three) == 3
