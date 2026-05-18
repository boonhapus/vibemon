import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy as sa

from app import models
from app.data_store import assets as ds_assets
from app.data_store import schema as ds_schema
from app.data_store import types as ds_types


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


async def _insert_vibemon(sess: AsyncSession, *, vibemon_id: uuid.UUID) -> None:
    seed = models.BirthSeed(id=uuid.uuid7(), timestamp=_utcnow(), geo_coords=[0.0, 0.0])
    snapshot = models.BirthSnapshot(
        id=uuid.uuid7(),
        birth_seed_id=seed.id,
        provider_payloads={"climate": {"ok": True}},
    )
    vibemon = models.Vibemon(
        id=vibemon_id,
        nickname="test",
        xp=0,
        level=1,
        evo_stage=1,
        lifecycle="born",
        disposition=None,
        team_slot=None,
        trainer_id=None,
        birth_snapshot_id=snapshot.id,
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
    )
    sess.add_all([seed, snapshot, vibemon])
    await sess.flush()


@pytest.mark.asyncio
async def test_delete_for_vibemon_deletes_rows_even_if_blob_delete_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as sess:
            vibemon_id = uuid.uuid7()
            await _insert_vibemon(sess, vibemon_id=vibemon_id)

            now = _utcnow()
            sess.add_all(
                [
                    models.VibemonAsset(
                        id=uuid.uuid7(),
                        vibemon_id=vibemon_id,
                        kind=ds_types.AssetKind.REFERENCE.value,
                        object_key="ok-key",
                        content_type="image/png",
                        byte_size=1,
                        sha256="a",
                        created_at=now,
                        updated_at=now,
                    ),
                    models.VibemonAsset(
                        id=uuid.uuid7(),
                        vibemon_id=vibemon_id,
                        kind=ds_types.AssetKind.SHEET.value,
                        object_key="fail-key",
                        content_type="image/png",
                        byte_size=1,
                        sha256="b",
                        created_at=now,
                        updated_at=now,
                    ),
                ]
            )
            await sess.commit()

            deleted_keys: list[str] = []

            async def fake_delete(key: str) -> None:
                deleted_keys.append(key)
                if key == "fail-key":
                    raise RuntimeError("delete failed")

            monkeypatch.setattr(ds_assets.monstore, "delete", fake_delete)

            rows_deleted = await ds_assets.delete_for_vibemon(sess, vibemon_id)
            await sess.commit()

            assert rows_deleted == 2
            assert deleted_keys == ["fail-key", "ok-key"]

            remaining = (
                (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)))
                .scalars()
                .all()
            )
            assert remaining == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_upsert_replacing_object_key_deletes_old_blob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as sess:
            vibemon_id = uuid.uuid7()
            await _insert_vibemon(sess, vibemon_id=vibemon_id)

            now = _utcnow()
            sess.add(
                models.VibemonAsset(
                    id=uuid.uuid7(),
                    vibemon_id=vibemon_id,
                    kind=ds_types.AssetKind.REFERENCE.value,
                    object_key="old-key",
                    content_type="image/png",
                    byte_size=1,
                    sha256="a",
                    created_at=now,
                    updated_at=now,
                )
            )
            await sess.commit()

            deleted_keys: list[str] = []

            async def fake_delete(key: str) -> None:
                deleted_keys.append(key)

            monkeypatch.setattr(ds_assets.monstore, "delete", fake_delete)

            await ds_assets.upsert(
                sess,
                vibemon_id,
                [
                    ds_schema.AssetRef(
                        vibemon_id=vibemon_id,
                        kind=ds_types.AssetKind.REFERENCE,
                        key="new-key",
                        content_type="image/png",
                        byte_size=2,
                        sha256="new",
                    )
                ],
            )
            await sess.commit()

            row = (
                await sess.execute(
                    sa.select(models.VibemonAsset).where(
                        models.VibemonAsset.vibemon_id == vibemon_id,
                        models.VibemonAsset.kind == ds_types.AssetKind.REFERENCE.value,
                    )
                )
            ).scalar_one()

            assert row.object_key == "new-key"
            assert deleted_keys == ["old-key"]
    finally:
        await engine.dispose()
