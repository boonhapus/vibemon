"""Encounter adjustment persistence."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.ids import TrainerIdT
from app.storage.database import models


async def upsert_encounter_adjustment(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    source: str,
    multiplier: float,
    starts_at: dt.datetime,
    ends_at: dt.datetime,
) -> None:
    adjustment = (
        await sess.execute(
            sa.select(models.EncounterAdjustment)
            .where(
                models.EncounterAdjustment.trainer_id == trainer_id,
                models.EncounterAdjustment.vibemon_id == vibemon_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if adjustment is None:
        adjustment = models.EncounterAdjustment(
            trainer_id=trainer_id,
            vibemon_id=vibemon_id,
            source=source,
            initial_multiplier=multiplier,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        sess.add(adjustment)
        return
    adjustment.source = source
    adjustment.initial_multiplier = multiplier
    adjustment.starts_at = starts_at
    adjustment.ends_at = ends_at
