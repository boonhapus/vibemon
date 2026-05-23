"""Prune asset rows and blobs for expired Vibemon."""

from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.time import resolve_clock
from app.domains.vibemon.disposition import VibemonDispositionT
from app.storage.blob import assets as blob_assets
from app.storage.database import models


async def prune_expired_assets(
    sess: AsyncSession,
    *,
    older_than: dt.timedelta = dt.timedelta(0),
    limit: int | None = None,
) -> int:
    cutoff = resolve_clock() - older_than
    stmt = (
        sa.select(models.Vibemon.id)
        .where(
            models.Vibemon.disposition == VibemonDispositionT.EXPIRED.value,
            models.Vibemon.expired_at.is_not(None),
            models.Vibemon.expired_at <= cutoff,
        )
        .order_by(models.Vibemon.expired_at.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    vibemon_ids = (await sess.execute(stmt)).scalars().all()

    deleted_rows = 0
    for vibemon_id in vibemon_ids:
        deleted_rows += await blob_assets.delete_for_vibemon(sess, vibemon_id)
    return deleted_rows
