"""One-off database repairs run at startup or from scripts."""

from collections import defaultdict
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.trainer import validation as trainer_validation
from app.storage.database import models


async def _reassign_trainer_rows(
    sess: AsyncSession,
    *,
    from_id: uuid.UUID,
    to_id: uuid.UUID,
) -> None:
    await sess.execute(
        sa.update(models.Vibemon).where(models.Vibemon.trainer_id == from_id).values(trainer_id=to_id)
    )
    await sess.execute(
        sa.update(models.BirthSeed).where(models.BirthSeed.trainer_id == from_id).values(trainer_id=to_id)
    )
    await sess.execute(
        sa.update(models.CandidateReview)
        .where(models.CandidateReview.trainer_id == from_id)
        .values(trainer_id=to_id)
    )

    for secret in (
        await sess.scalars(sa.select(models.TrainerSecret).where(models.TrainerSecret.trainer_id == from_id))
    ).all():
        keeper_has = await sess.scalar(
            sa.select(
                sa.exists().where(
                    models.TrainerSecret.trainer_id == to_id,
                    models.TrainerSecret.kind == secret.kind,
                )
            )
        )
        if keeper_has:
            await sess.delete(secret)
        else:
            secret.trainer_id = to_id

    for credit_day in (
        await sess.scalars(
            sa.select(models.GenerationCreditDay).where(models.GenerationCreditDay.trainer_id == from_id)
        )
    ).all():
        keeper_has = await sess.scalar(
            sa.select(
                sa.exists().where(
                    models.GenerationCreditDay.trainer_id == to_id,
                    models.GenerationCreditDay.credit_date == credit_day.credit_date,
                )
            )
        )
        if keeper_has:
            await sess.delete(credit_day)
        else:
            credit_day.trainer_id = to_id

    for adjustment in (
        await sess.scalars(
            sa.select(models.EncounterAdjustment).where(models.EncounterAdjustment.trainer_id == from_id)
        )
    ).all():
        keeper_has = await sess.scalar(
            sa.select(
                sa.exists().where(
                    models.EncounterAdjustment.trainer_id == to_id,
                    models.EncounterAdjustment.vibemon_id == adjustment.vibemon_id,
                )
            )
        )
        if keeper_has:
            await sess.delete(adjustment)
        else:
            adjustment.trainer_id = to_id


async def repair_trainer_usernames(sess: AsyncSession) -> None:
    """Normalize stored trainer names and merge case-insensitive duplicates."""
    trainers = (await sess.scalars(sa.select(models.Trainer))).all()
    groups: dict[str, list[models.Trainer]] = defaultdict(list)
    for trainer in trainers:
        groups[trainer_validation.normalize_username(trainer.username)].append(trainer)

    for canonical, group in groups.items():
        group.sort(key=lambda trainer: trainer.id)
        keeper = group[0]

        for duplicate in group[1:]:
            await _reassign_trainer_rows(sess, from_id=duplicate.id, to_id=keeper.id)
            await sess.delete(duplicate)

        if len(group) > 1:
            await sess.flush()

        if keeper.username != canonical:
            keeper.username = canonical

    await sess.flush()
