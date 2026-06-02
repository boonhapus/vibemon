"""Release an owned Vibemon back to wild supply."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.errors import ReleaseUnavailable
from app.core.ids import TrainerIdT
from app.core.time import resolve_clock
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.schema import PublicVibemon
from app.storage.database import models, repositories
from app.workflows import _workflow_support as workflows


async def release_vibemon(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> PublicVibemon:
    now = resolve_clock()
    row = (
        await sess.execute(
            sa.select(models.Vibemon)
            .where(
                models.Vibemon.id == vibemon_id,
                models.Vibemon.trainer_id == trainer_id,
                models.Vibemon.disposition == VibemonDispositionT.OWNED.value,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise ReleaseUnavailable("Vibemon is not owned by this trainer.")
    workflows.release_to_wild(sess, row, trainer_id, now)
    await sess.flush()
    loaded = await repositories.load_vibemon(sess, vibemon_id)
    return await workflows.public_vibemon(loaded, reviewing_trainer_id=trainer_id)
