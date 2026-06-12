"""Persist domain asset refs to slot tables.

Blob bytes live in :mod:`app.storage.blob.monstore`; this module keeps slot rows
in sync. Revisions are append-only — older blobs are retained.
"""

from collections.abc import Iterable
from typing import Any, cast
import hashlib
import uuid

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
import structlog

from app.core.time import resolve_clock
from app.domains.trainer import assets as trainer_assets
from app.domains.vibemon.assets import AssetKind, AssetRef
from app.storage.blob import const as blob_const
from app.storage.blob.monstore import MonStore, get_default_monstore
from app.storage.database import models

_LOGGER = structlog.get_logger(__name__)


async def persist_vibemon_slots(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    refs: Iterable[AssetRef],
) -> None:
    """Upsert Vibemon slot rows from refs written to monstore. Caller commits."""
    refs = list(refs)
    if not refs:
        return
    mismatched_refs = [ref for ref in refs if ref.vibemon_id != vibemon_id]
    if mismatched_refs:
        raise ValueError("AssetRef vibemon_id must match the target Vibemon")

    existing = (
        (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)))
        .scalars()
        .all()
    )
    existing_by_kind = {row.kind: row for row in existing}
    now = resolve_clock()

    for ref in refs:
        row = existing_by_kind.get(ref.kind.value)
        if row is None:
            sess.add(
                models.VibemonAsset(
                    vibemon_id=ref.vibemon_id,
                    kind=ref.kind.value,
                    selected_revision=ref.revision,
                    max_revision=ref.revision,
                    object_key=ref.key,
                    content_type=ref.content_type,
                    byte_size=ref.byte_size,
                    sha256=ref.sha256,
                    display_anchor=ref.anchor.model_dump() if ref.anchor else None,
                    created_at=now,
                    updated_at=now,
                )
            )
            continue

        if ref.revision > row.max_revision:
            row.max_revision = ref.revision
            row.selected_revision = ref.revision
            row.object_key = ref.key
            row.content_type = ref.content_type
            row.byte_size = ref.byte_size
            row.sha256 = ref.sha256
            row.display_anchor = ref.anchor.model_dump() if ref.anchor else None
            row.updated_at = now
        elif ref.revision == row.selected_revision:
            row.object_key = ref.key
            row.content_type = ref.content_type
            row.byte_size = ref.byte_size
            row.sha256 = ref.sha256
            row.display_anchor = ref.anchor.model_dump() if ref.anchor else None
            row.updated_at = now


async def append_trainer_asset(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    kind: trainer_assets.TrainerAssetKind,
    data: bytes,
    *,
    content_type: str | None = None,
    monstore: MonStore | None = None,
) -> models.TrainerAsset:
    """Write a new trainer asset revision and upsert its slot row. Caller commits."""
    asset_store = monstore or get_default_monstore()
    resolved_content_type = content_type or blob_const.CONTENT_TYPE_BY_EXTENSION.get(
        kind.value.rsplit(".", 1)[-1].lower(),
        "application/octet-stream",
    )
    row = (
        await sess.execute(
            sa.select(models.TrainerAsset).where(
                models.TrainerAsset.trainer_id == trainer_id,
                models.TrainerAsset.kind == kind.value,
            )
        )
    ).scalar_one_or_none()
    revision = (row.max_revision if row is not None else 0) + 1
    key = asset_store.trainer_asset_key(trainer_id, kind, revision)
    await asset_store.put_bytes(key, data)
    sha256 = hashlib.sha256(data).hexdigest()
    now = resolve_clock()

    if row is None:
        row = models.TrainerAsset(
            trainer_id=trainer_id,
            kind=kind.value,
            selected_revision=revision,
            max_revision=revision,
            object_key=key,
            content_type=resolved_content_type,
            byte_size=len(data),
            sha256=sha256,
            created_at=now,
            updated_at=now,
        )
        sess.add(row)
        return row

    row.selected_revision = revision
    row.max_revision = revision
    row.object_key = key
    row.content_type = resolved_content_type
    row.byte_size = len(data)
    row.sha256 = sha256
    row.updated_at = now
    return row


async def delete_object_keys(
    object_keys: Iterable[str],
    *,
    monstore: MonStore | None = None,
) -> tuple[int, int]:
    """Best-effort delete for known blob keys.

    Returns ``(deleted, failed)``; failures are logged and do not raise.
    """
    asset_store = monstore or get_default_monstore()
    deleted = 0
    failed = 0
    for key in sorted(set(object_keys)):
        try:
            await asset_store.delete(key)
            deleted += 1
        except Exception:
            failed += 1
            await _LOGGER.awarning("Failed to delete monstore object", key=key, exc_info=True)
    return deleted, failed


def vibemon_revision_keys(
    vibemon_id: uuid.UUID,
    row: models.VibemonAsset,
    *,
    monstore: MonStore | None = None,
) -> list[str]:
    """Return monstore keys for every revision stored on one Vibemon slot."""
    asset_store = monstore or get_default_monstore()
    kind = AssetKind(row.kind)
    return [asset_store.vibemon_asset_key(vibemon_id, kind, revision) for revision in range(1, row.max_revision + 1)]


def trainer_revision_keys(
    trainer_id: uuid.UUID,
    row: models.TrainerAsset,
    *,
    monstore: MonStore | None = None,
) -> list[str]:
    """Return monstore keys for every revision stored on one trainer slot."""
    asset_store = monstore or get_default_monstore()
    kind = trainer_assets.TrainerAssetKind(row.kind)
    return [asset_store.trainer_asset_key(trainer_id, kind, revision) for revision in range(1, row.max_revision + 1)]


async def delete_for_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    monstore: MonStore | None = None,
) -> int:
    """Delete all revision blobs and slot rows for a Vibemon. Returns DB row count removed."""
    rows = (
        (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)))
        .scalars()
        .all()
    )
    object_keys = [key for row in rows for key in vibemon_revision_keys(vibemon_id, row, monstore=monstore)]

    _, failed = await delete_object_keys(object_keys, monstore=monstore)

    delete_query = sa.delete(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)
    result = await sess.execute(delete_query)
    deleted_rows = cast(CursorResult[Any], result)

    if failed:
        await _LOGGER.awarning(
            "Deleted asset rows with blob-delete failures",
            vibemon_id=str(vibemon_id),
            failed_blob_deletes=failed,
        )

    return deleted_rows.rowcount or 0
