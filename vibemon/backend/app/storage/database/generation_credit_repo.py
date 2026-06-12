"""Generation credit day persistence."""

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.ids import TrainerIdT
from app.storage.database import models


async def credit_day(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    credit_date: dt.date,
) -> models.GenerationCreditDay:
    row = (
        await sess.execute(
            sa.select(models.GenerationCreditDay)
            .where(
                models.GenerationCreditDay.trainer_id == trainer_id,
                models.GenerationCreditDay.credit_date == credit_date,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        row = models.GenerationCreditDay(trainer_id=trainer_id, credit_date=credit_date)
        sess.add(row)
        await sess.flush()
    return row
