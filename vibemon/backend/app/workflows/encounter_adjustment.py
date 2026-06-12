"""Encounter-rate adjustment side effects from candidate and crew actions."""

import datetime as dt
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.domains.encounter import tuning as encounter_tuning
from app.storage.database import encounter_adjustment_repo


async def upsert_encounter_adjustment(
    sess: AsyncSession,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    source: str,
    now: dt.datetime,
) -> None:
    multiplier = encounter_tuning.ADJUSTMENT_MULTIPLIER_BY_SOURCE.get(source)
    if multiplier is None:
        raise ValueError(f"Unknown encounter adjustment source: {source}")
    ends_at = now + encounter_tuning.cooldown_duration(random.Random())
    await encounter_adjustment_repo.upsert_encounter_adjustment(
        sess,
        trainer_id=trainer_id,
        vibemon_id=vibemon_id,
        source=source,
        multiplier=multiplier,
        starts_at=now,
        ends_at=ends_at,
    )
