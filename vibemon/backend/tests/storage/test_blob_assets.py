from types import SimpleNamespace
from typing import cast
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.vibemon.assets import ASSET_VERSION, AssetKind, AssetRef
from app.storage.blob import assets as blob_assets
from app.storage.blob.monstore import MonStore
from app.storage.database import models


def _asset_ref(vibemon_id: uuid.UUID, key: str, *, kind: AssetKind = AssetKind.REFERENCE) -> AssetRef:
    return AssetRef(
        vibemon_id=vibemon_id,
        kind=kind,
        key=key,
        content_type="image/png",
        byte_size=12,
        sha256="abc123",
        version=ASSET_VERSION,
    )


@pytest.mark.asyncio
async def test_upsert_creates_and_replaces_asset_rows(
    sess: AsyncSession,
) -> None:
    vibemon_id = uuid.uuid7()
    deleted_keys: list[str] = []

    async def fake_delete(key: str) -> None:
        deleted_keys.append(key)

    fake_monstore = cast(MonStore, SimpleNamespace(delete=fake_delete))

    await blob_assets.upsert(sess, vibemon_id, [_asset_ref(vibemon_id, "first.png")], monstore=fake_monstore)
    await sess.flush()
    await blob_assets.upsert(sess, vibemon_id, [_asset_ref(vibemon_id, "second.png")], monstore=fake_monstore)
    await sess.flush()

    rows = (await sess.execute(sa.select(models.VibemonAsset))).scalars().all()
    assert len(rows) == 1
    assert rows[0].vibemon_id == vibemon_id
    assert rows[0].kind == AssetKind.REFERENCE.value
    assert rows[0].object_key == "second.png"
    assert deleted_keys == ["first.png"]


@pytest.mark.asyncio
async def test_upsert_rejects_refs_for_a_different_vibemon(sess: AsyncSession) -> None:
    target_id = uuid.uuid7()
    ref = _asset_ref(uuid.uuid7(), "wrong-owner.png")

    with pytest.raises(ValueError, match="vibemon_id"):
        await blob_assets.upsert(sess, target_id, [ref])


@pytest.mark.asyncio
async def test_delete_for_vibemon_deletes_rows_and_best_effort_blobs(
    sess: AsyncSession,
) -> None:
    vibemon_id = uuid.uuid7()
    other_vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0)
    sess.add_all(
        [
            models.VibemonAsset(
                vibemon_id=vibemon_id,
                kind=AssetKind.REFERENCE.value,
                object_key="delete-me.png",
                content_type="image/png",
                byte_size=10,
                sha256="abc",
                created_at=now,
                updated_at=now,
            ),
            models.VibemonAsset(
                vibemon_id=vibemon_id,
                kind=AssetKind.SHEET.value,
                object_key="fail-me.png",
                content_type="image/png",
                byte_size=10,
                sha256="def",
                created_at=now,
                updated_at=now,
            ),
            models.VibemonAsset(
                vibemon_id=other_vibemon_id,
                kind=AssetKind.REFERENCE.value,
                object_key="keep-me.png",
                content_type="image/png",
                byte_size=10,
                sha256="ghi",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    await sess.flush()
    deleted_keys: list[str] = []

    async def fake_delete(key: str) -> None:
        if key == "fail-me.png":
            raise RuntimeError("delete failed")
        deleted_keys.append(key)

    fake_monstore = cast(MonStore, SimpleNamespace(delete=fake_delete))

    deleted_rows = await blob_assets.delete_for_vibemon(sess, vibemon_id, monstore=fake_monstore)

    remaining = (await sess.execute(sa.select(models.VibemonAsset))).scalars().all()
    assert deleted_rows == 2
    assert deleted_keys == ["delete-me.png"]
    assert [row.object_key for row in remaining] == ["keep-me.png"]
