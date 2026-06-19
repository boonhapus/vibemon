"""Vibemon history event persistence."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import models


async def load_history_events(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
) -> tuple[dict[str, object], ...]:
    rows = (
        await sess.execute(
            sa.select(models.VibemonHistory)
            .where(models.VibemonHistory.vibemon_id == vibemon_id)
            .order_by(models.VibemonHistory.occurred_at, models.VibemonHistory.id)
        )
    ).scalars().all()
    return tuple({"event_type": row.event_type, "payload": dict(row.payload)} for row in rows)


def add_history(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    event: VibemonHistoryEventT,
    occurred_at: dt.datetime,
    payload: dict[str, str],
) -> None:
    row = models.VibemonHistory(
        vibemon_id=vibemon_id,
        event_type=event.value,
        occurred_at=occurred_at,
        payload=payload,
    )
    sess.add(row)
