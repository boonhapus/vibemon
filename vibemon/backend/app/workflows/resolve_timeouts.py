"""Resolve stale review and generation-hold timeouts."""

from typing import Any, cast
import datetime as dt

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.time import resolve_clock
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.trainer.credits import GENERATION_HOLD_TIMEOUT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import models
from app.workflows import wild_disposition


async def resolve_review_timeouts(
    sess: AsyncSession,
) -> int:
    now = resolve_clock()
    reviews = (
        (
            await sess.execute(
                sa.select(models.CandidateReview)
                .options(selectinload(models.CandidateReview.vibemon))
                .where(
                    models.CandidateReview.status == CandidateReviewStatusT.PENDING.value,
                    models.CandidateReview.timeout_at <= now,
                )
            )
        )
        .scalars()
        .all()
    )
    for review in reviews:
        await wild_disposition.resolve_candidate_to_wild(
            sess,
            review,
            now,
            status=CandidateReviewStatusT.TIMED_OUT,
            event=VibemonHistoryEventT.CANDIDATE_TIMED_OUT,
        )
    await sess.flush()
    return len(reviews)


async def resolve_stale_holds(
    sess: AsyncSession,
    *,
    timeout: dt.timedelta = GENERATION_HOLD_TIMEOUT,
) -> int:
    now = resolve_clock()
    threshold = now - timeout
    result = await sess.execute(
        sa.update(models.GenerationCreditDay)
        .where(
            models.GenerationCreditDay.active_hold_id.is_not(None),
            models.GenerationCreditDay.hold_started_at <= threshold,
        )
        .values(active_hold_id=None, hold_started_at=None)
    )
    return cast(CursorResult[Any], result).rowcount or 0
