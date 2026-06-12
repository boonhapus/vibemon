import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.trainer import assets as trainer_assets
from app.domains.vibemon.assets import ASSET_VERSION, AssetKind, AssetRef
from app.storage.blob import assets as blob_assets
from app.storage.blob.monstore import MonStore
from app.storage.database import models


def _asset_ref(
    vibemon_id: uuid.UUID,
    key: str,
    *,
    kind: AssetKind = AssetKind.REFERENCE,
    revision: int = 1,
) -> AssetRef:
    return AssetRef(
        vibemon_id=vibemon_id,
        kind=kind,
        revision=revision,
        key=key,
        content_type="image/png",
        byte_size=12,
        sha256="abc123",
        version=ASSET_VERSION,
    )


@pytest.mark.asyncio
async def test_persist_vibemon_slots_creates_and_appends_without_deleting_blobs(
    sess: AsyncSession,
) -> None:
    vibemon_id = uuid.uuid7()

    await blob_assets.persist_vibemon_slots(
        sess,
        vibemon_id,
        [_asset_ref(vibemon_id, "first.png", revision=1)],
    )
    await sess.flush()
    await blob_assets.persist_vibemon_slots(
        sess,
        vibemon_id,
        [_asset_ref(vibemon_id, "second.png", revision=2)],
    )
    await sess.flush()

    rows = (await sess.execute(sa.select(models.VibemonAsset))).scalars().all()
    assert len(rows) == 1
    assert rows[0].vibemon_id == vibemon_id
    assert rows[0].kind == AssetKind.REFERENCE.value
    assert rows[0].selected_revision == 2
    assert rows[0].max_revision == 2
    assert rows[0].object_key == "second.png"


@pytest.mark.asyncio
async def test_persist_vibemon_slots_rejects_refs_for_a_different_vibemon(sess: AsyncSession) -> None:
    target_id = uuid.uuid7()
    ref = _asset_ref(uuid.uuid7(), "wrong-owner.png")

    with pytest.raises(ValueError, match="vibemon_id"):
        await blob_assets.persist_vibemon_slots(sess, target_id, [ref])


@pytest.mark.asyncio
async def test_append_trainer_asset_increments_revision(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    monstore = MonStore("memory://")

    first = await blob_assets.append_trainer_asset(
        sess,
        trainer_id,
        trainer_assets.TrainerAssetKind.REFERENCE,
        b"first",
        monstore=monstore,
    )
    first_key = first.object_key
    await sess.flush()
    second = await blob_assets.append_trainer_asset(
        sess,
        trainer_id,
        trainer_assets.TrainerAssetKind.REFERENCE,
        b"second",
        monstore=monstore,
    )
    await sess.flush()

    assert first_key != second.object_key
    assert second.selected_revision == 2
    assert second.max_revision == 2
    assert await monstore.has(first_key)
    assert await monstore.has(second.object_key)


@pytest.mark.asyncio
async def test_delete_for_vibemon_deletes_all_revision_blobs(
    sess: AsyncSession,
) -> None:
    vibemon_id = uuid.uuid7()
    other_vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0)
    monstore = MonStore("memory://")
    reference_kind = AssetKind.REFERENCE.value
    reference_key_r1 = monstore.vibemon_asset_key(vibemon_id, AssetKind.REFERENCE, revision=1)
    reference_key_r2 = monstore.vibemon_asset_key(vibemon_id, AssetKind.REFERENCE, revision=2)
    sheet_key_r1 = monstore.vibemon_asset_key(vibemon_id, AssetKind.SHEET, revision=1)
    await monstore.put_bytes(reference_key_r1, b"ref-1")
    await monstore.put_bytes(reference_key_r2, b"ref-2")
    await monstore.put_bytes(sheet_key_r1, b"sheet-1")
    await monstore.put_bytes("keep-me.png", b"keep")

    sess.add_all(
        [
            models.VibemonAsset(
                vibemon_id=vibemon_id,
                kind=reference_kind,
                selected_revision=2,
                max_revision=2,
                object_key=reference_key_r2,
                content_type="image/png",
                byte_size=10,
                sha256="abc",
                created_at=now,
                updated_at=now,
            ),
            models.VibemonAsset(
                vibemon_id=vibemon_id,
                kind=AssetKind.SHEET.value,
                selected_revision=1,
                max_revision=1,
                object_key=sheet_key_r1,
                content_type="image/png",
                byte_size=10,
                sha256="def",
                created_at=now,
                updated_at=now,
            ),
            models.VibemonAsset(
                vibemon_id=other_vibemon_id,
                kind=reference_kind,
                selected_revision=1,
                max_revision=1,
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
    tracking_monstore = MonStore("memory://")
    tracking_monstore.vibemon_asset_key = monstore.vibemon_asset_key  # type: ignore[method-assign]

    async def fake_delete(key: str) -> None:
        if key == sheet_key_r1:
            raise RuntimeError("delete failed")
        deleted_keys.append(key)

    tracking_monstore.delete = fake_delete  # type: ignore[method-assign]

    deleted_rows = await blob_assets.delete_for_vibemon(sess, vibemon_id, monstore=tracking_monstore)

    remaining = (await sess.execute(sa.select(models.VibemonAsset))).scalars().all()
    assert deleted_rows == 2
    assert set(deleted_keys) == {reference_key_r1, reference_key_r2}
    assert [row.object_key for row in remaining] == ["keep-me.png"]
