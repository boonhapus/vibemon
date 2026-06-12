"""Vibemon history event persistence."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import models


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
