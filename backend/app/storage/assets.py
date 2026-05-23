"""Persist ``AssetRef`` rows to the ``vibemon_asset`` table."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast
import datetime as dt
import uuid

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
import structlog

from app import models
from app.storage import monstore
from app.storage import schema as ds_schema

_LOGGER = structlog.get_logger(__name__)


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


async def upsert(sess: AsyncSession, vibemon_id: uuid.UUID, refs: Iterable[ds_schema.AssetRef]) -> None:
    """Upsert one or more asset rows by ``(vibemon_id, kind)``.

    Preserves ``created_at`` on update; refreshes content metadata and
    ``updated_at``. Caller commits.
    """
    refs = list(refs)
    if not refs:
        return

    existing = (
        (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)))
        .scalars()
        .all()
    )
    existing_by_kind = {row.kind: row for row in existing}

    now = _utcnow()
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

    await delete_object_keys(replaced_keys)


async def delete_object_keys(object_keys: Iterable[str]) -> tuple[int, int]:
    """Best-effort delete for known blob keys.

    Returns ``(deleted, failed)``; failures are logged and do not raise.
    """
    deleted = 0
    failed = 0
    for key in sorted(set(object_keys)):
        try:
            await monstore.delete(key)
            deleted += 1
        except Exception:
            failed += 1
            await _LOGGER.awarning("Failed to delete monstore object", key=key, exc_info=True)
    return deleted, failed


async def delete_for_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> int:
    """Delete asset blobs and rows for a Vibemon. Returns DB row count removed."""
    q = sa.select(models.VibemonAsset.object_key).where(models.VibemonAsset.vibemon_id == vibemon_id)

    r = await sess.execute(q)
    d = r.scalars().all()

    _, failed = await delete_object_keys(d)

    q = sa.delete(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)
    r = await sess.execute(q)
    d = cast(CursorResult[Any], r)

    if failed:
        await _LOGGER.awarning(
            "Deleted asset rows with blob-delete failures",
            vibemon_id=str(vibemon_id),
            failed_blob_deletes=failed,
        )

    return d.rowcount or 0
