"""Candidate review persistence."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.errors import CandidateReviewUnavailable
from app.core.ids import TrainerIdT
from app.domains.adoption import policy as adoption_policy
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.generation.types import ProviderWarning
from app.storage.database import models


def create_review(
    vibemon_id: uuid.UUID,
    trainer_id: TrainerIdT,
    now: dt.datetime,
    *,
    timeout: dt.timedelta,
    provider_notes: tuple[ProviderWarning, ...] = (),
) -> models.CandidateReview:
    return models.CandidateReview(
        vibemon_id=vibemon_id,
        trainer_id=trainer_id,
        status=CandidateReviewStatusT.PENDING.value,
        shown_at=now,
        timeout_at=now + timeout,
        resolved_at=None,
        resolution=None,
        provider_notes=[note.model_dump(mode="json") for note in provider_notes],
    )


async def load_pending_candidate_review(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
) -> models.CandidateReview | None:
    return (
        await sess.execute(
            sa.select(models.CandidateReview)
            .options(
                selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.identity),
                selectinload(models.CandidateReview.vibemon)
                .selectinload(models.Vibemon.moves)
                .selectinload(models.VibemonMove.move),
                selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.assets),
            )
            .where(
                models.CandidateReview.trainer_id == trainer_id,
                models.CandidateReview.status == CandidateReviewStatusT.PENDING.value,
            )
            .order_by(models.CandidateReview.shown_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def pending_review(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> models.CandidateReview:
    review = (
        await sess.execute(
            sa.select(models.CandidateReview)
            .options(
                selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.identity),
                selectinload(models.CandidateReview.vibemon)
                .selectinload(models.Vibemon.moves)
                .selectinload(models.VibemonMove.move),
                selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.assets),
            )
            .where(
                models.CandidateReview.trainer_id == trainer_id,
                models.CandidateReview.vibemon_id == vibemon_id,
                models.CandidateReview.status == CandidateReviewStatusT.PENDING.value,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if review is None:
        raise CandidateReviewUnavailable("No pending candidate review exists for this trainer and Vibemon.")
    adoption_policy.require_pending_review_status(review.status)
    return review
