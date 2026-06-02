"""Persist domain asset refs to the ``vibemon_asset`` table.

Blob bytes live in :mod:`app.storage.blob.monstore`; this module keeps the
database rows in sync and performs best-effort blob cleanup on replace/delete.
"""

from collections.abc import Iterable
from typing import Any, cast
import uuid

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
import structlog

from app.core.time import resolve_clock
from app.domains.vibemon.assets import AssetRef
from app.storage.blob.monstore import MonStore, get_default_monstore
from app.storage.database import models

_LOGGER = structlog.get_logger(__name__)


async def upsert(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    refs: Iterable[AssetRef],
    *,
    monstore: MonStore | None = None,
) -> None:
    """Upsert one or more asset rows by ``(vibemon_id, kind)``.

    Preserves ``created_at`` on update; refreshes content metadata and
    ``updated_at``. Caller commits.
    """
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
    replaced_keys: list[str] = []

    for ref in refs:
        row = existing_by_kind.get(ref.kind.value)

        if row is None:
            sess.add(
                models.VibemonAsset(
                    vibemon_id=ref.vibemon_id,
                    kind=ref.kind.value,
                    object_key=ref.key,
                    content_type=ref.content_type,
                    byte_size=ref.byte_size,
                    sha256=ref.sha256,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            if row.object_key != ref.key:
                replaced_keys.append(row.object_key)
            row.object_key = ref.key
            row.content_type = ref.content_type
            row.byte_size = ref.byte_size
            row.sha256 = ref.sha256
            row.updated_at = now

    await delete_object_keys(replaced_keys, monstore=monstore)


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


async def delete_for_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    monstore: MonStore | None = None,
) -> int:
    """Delete asset blobs and rows for a Vibemon. Returns DB row count removed."""
    object_key_query = sa.select(models.VibemonAsset.object_key).where(models.VibemonAsset.vibemon_id == vibemon_id)

    result = await sess.execute(object_key_query)
    object_keys = result.scalars().all()

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
