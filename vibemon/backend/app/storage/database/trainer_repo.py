"""Trainer and crew persistence."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.ids import TrainerIdT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.storage.database import models


async def lock_trainer(sess: AsyncSession, trainer_id: TrainerIdT) -> None:
    await sess.execute(sa.select(models.Trainer.id).where(models.Trainer.id == trainer_id).with_for_update())


async def get_trainer_by_username(sess: AsyncSession, username: str) -> models.Trainer | None:
    canonical = username.casefold()
    return (
        await sess.execute(sa.select(models.Trainer).where(models.Trainer.username == canonical))
    ).scalar_one_or_none()


async def count_owned_vibemons(sess: AsyncSession, trainer_id: TrainerIdT) -> int:
    return int(
        (
            await sess.execute(
                sa.select(sa.func.count())
                .select_from(models.Vibemon)
                .where(
                    models.Vibemon.trainer_id == trainer_id,
                    models.Vibemon.disposition == VibemonDispositionT.OWNED.value,
                )
            )
        ).scalar_one()
    )


async def load_owned_vibemons(sess: AsyncSession, trainer_id: TrainerIdT) -> list[models.Vibemon]:
    return list(
        (
            await sess.execute(
                sa.select(models.Vibemon)
                .options(
                    selectinload(models.Vibemon.identity),
                    selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                    selectinload(models.Vibemon.assets),
                    selectinload(models.Vibemon.candidate_reviews),
                    selectinload(models.Vibemon.birth_snapshot),
                )
                .where(
                    models.Vibemon.trainer_id == trainer_id,
                    models.Vibemon.disposition == VibemonDispositionT.OWNED.value,
                )
                .order_by(models.Vibemon.crew_slot)
            )
        )
        .scalars()
        .all()
    )
