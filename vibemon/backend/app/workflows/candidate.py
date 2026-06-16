"""Candidate Vibemon lifecycle: generate → adopt / reject."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import sqlalchemy as sa
import structlog

from app.core.errors import CandidateReviewUnavailable
from app.core.ids import TrainerIdT
from app.core.time import resolve_clock
from app.domains.adoption import policy as adoption_policy
from app.domains.adoption.candidate import CANDIDATE_REVIEW_TIMEOUT
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.generation.seed import BirthSeed
from app.domains.trainer import credits, crew
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import (
    candidate_review_repo,
    generation_credit_repo,
    history_repo,
    mapper,
    models,
    trainer_repo,
    vibemon_repo,
)
from app.workflows import birth_persist, public_projection, wild_disposition
from app.workflows.materialize_vibemon import MaterializeVibemon
from app.workflows.reference_facing import resolve_reference_facing

_LOGGER = structlog.get_logger(__name__)


async def generate_candidate(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    birth_seed: BirthSeed,
    nickname: str | None = None,
    bypass_credits: bool = False,
    christen: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    credit_day: models.GenerationCreditDay | None = None
    hold_id: uuid.UUID | None = None
    if not bypass_credits:
        credit_day, hold_id = await _reserve_credit(sess, trainer_id=trainer_id, now=now)
    try:
        row, provider_notes = await birth_persist.birth_and_persist_vibemon(
            sess,
            birth_seed=birth_seed,
            nickname=nickname,
            now=now,
            christen=christen,
        )
        review = candidate_review_repo.create_review(
            row.id,
            trainer_id,
            now,
            timeout=CANDIDATE_REVIEW_TIMEOUT,
            provider_notes=provider_notes,
        )
        sess.add(review)
        history_repo.add_history(
            sess,
            row.id,
            VibemonHistoryEventT.CANDIDATE_SHOWN,
            now,
            {"trainer_id": str(trainer_id)},
        )
        if credit_day is not None and hold_id is not None:
            await _consume_credit(sess, credit_day, hold_id)
        await sess.flush()
        loaded = await vibemon_repo.load_vibemon(sess, row.id)
        return await public_projection.public_vibemon(loaded, reviewing_trainer_id=trainer_id)
    except Exception:
        if credit_day is not None and hold_id is not None:
            await _release_credit(sess, credit_day, hold_id)
        await sess.flush()
        raise


async def adopt_candidate(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    release_vibemon_id: uuid.UUID | None = None,
    nickname: str | None = None,
    manifest: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    if adoption_policy.review_deadline_passed(timeout_at=review.timeout_at, now=now):
        await wild_disposition.resolve_candidate_to_wild(
            sess,
            review,
            now,
            status=CandidateReviewStatusT.TIMED_OUT,
            event=VibemonHistoryEventT.CANDIDATE_TIMED_OUT,
        )
        await sess.flush()
        raise CandidateReviewUnavailable("Candidate review has timed out.")

    slot, release_row = await _adoption_plan(sess, trainer_id=trainer_id, release_vibemon_id=release_vibemon_id)
    vibemon = await mapper.vibemon_from_row(review.vibemon)
    if nickname is not None:
        trimmed = nickname.strip()
        vibemon.nickname = trimmed or None
    if manifest and vibemon.lifecycle is not VibemonLifecycleT.MANIFESTED:
        vibemon = await MaterializeVibemon().manifest(vibemon)

    if release_row is not None:
        wild_disposition.release_to_wild(sess, release_row, trainer_id, now)
    mapper.apply_adopted_vibemon_to_row(review.vibemon, vibemon, trainer_id=trainer_id, crew_slot=slot)
    review.status = CandidateReviewStatusT.ADOPTED.value
    review.resolution = CandidateReviewStatusT.ADOPTED.value
    review.resolved_at = now
    await vibemon_repo.persist_assets(sess, vibemon)
    history_repo.add_history(
        sess,
        review.vibemon_id,
        VibemonHistoryEventT.CANDIDATE_ADOPTED,
        now,
        {"trainer_id": str(trainer_id)},
    )
    await sess.flush()
    loaded = await vibemon_repo.load_vibemon(sess, vibemon_id)
    return await public_projection.public_vibemon(loaded, reviewing_trainer_id=trainer_id)


async def reject_candidate(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> PublicVibemon:
    now = resolve_clock()
    crew_count = await trainer_repo.count_owned_vibemons(sess, trainer_id)
    if crew_count == 0:
        raise CandidateReviewUnavailable("Adopt your first Vibemon before passing on another.")
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    await wild_disposition.resolve_candidate_to_wild(
        sess,
        review,
        now,
        status=CandidateReviewStatusT.REJECTED,
        event=VibemonHistoryEventT.CANDIDATE_REJECTED,
    )
    await sess.flush()
    loaded = await vibemon_repo.load_vibemon(sess, vibemon_id)
    return await public_projection.public_vibemon(loaded, reviewing_trainer_id=trainer_id)


async def record_candidate_review_facing(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> str:
    """Persist hatch UI facing on the pending review and vibemon row after generate."""
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    facing = resolve_reference_facing(vibemon)
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    review.reference_facing = facing
    row.reference_detected_facing = (
        vibemon.reference_detected_facing.value if vibemon.reference_detected_facing else None
    )
    return facing


async def refresh_candidate_display_assets(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> str:
    """Regenerate the candidate's reference assets and return the refreshed facing."""
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    vibemon = await mapper.vibemon_from_row(review.vibemon)
    vibemon = await MaterializeVibemon().regenerate_display_assets(vibemon)
    mapper.apply_vibemon_to_row(review.vibemon, vibemon)
    await vibemon_repo.persist_assets(sess, vibemon)
    facing = resolve_reference_facing(vibemon)
    review.reference_facing = facing
    return facing


async def manifest_adopted_vibemon(
    vibemon_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Manifest an owned Vibemon in its own session; safe as a background task."""
    async with session_factory() as sess:
        try:
            row = await vibemon_repo.load_vibemon(sess, vibemon_id)
            vibemon = await mapper.vibemon_from_row(row)
            if vibemon.lifecycle is VibemonLifecycleT.MANIFESTED:
                return
            vibemon = await MaterializeVibemon().manifest(vibemon)
            mapper.apply_vibemon_to_row(row, vibemon)
            await vibemon_repo.persist_assets(sess, vibemon)
            await sess.commit()
            await _LOGGER.ainfo("background_manifest_complete", vibemon_id=str(vibemon_id))
        except Exception as exc:
            await sess.rollback()
            await _LOGGER.aerror("background_manifest_failed", vibemon_id=str(vibemon_id), error=str(exc))


async def _adoption_plan(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    release_vibemon_id: uuid.UUID | None,
) -> tuple[int, models.Vibemon | None]:
    """Lock and fetch crew rows, then let the domain decide the adoption plan."""
    await trainer_repo.lock_trainer(sess, trainer_id)
    rows = (
        (
            await sess.execute(
                sa.select(models.Vibemon)
                .where(
                    models.Vibemon.trainer_id == trainer_id,
                    models.Vibemon.disposition == VibemonDispositionT.OWNED.value,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    plan = crew.plan_adoption(
        owned=[crew.CrewMember(vibemon_id=row.id, crew_slot=row.crew_slot) for row in rows],
        release_vibemon_id=release_vibemon_id,
    )
    release_row = next((row for row in rows if row.id == plan.release_vibemon_id), None)
    return plan.slot, release_row


async def _reserve_credit(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    now: dt.datetime,
) -> tuple[models.GenerationCreditDay, uuid.UUID]:
    await trainer_repo.lock_trainer(sess, trainer_id)
    row = await generation_credit_repo.credit_day(sess, trainer_id=trainer_id, credit_date=now.date())
    hold_id = credits.reserve_generation_credit(row, now=now)  # pyrefly: ignore
    await sess.flush()
    return row, hold_id


async def _consume_credit(
    sess: AsyncSession,
    row: models.GenerationCreditDay,
    hold_id: uuid.UUID,
) -> None:
    credits.consume_generation_credit(row, hold_id)  # pyrefly: ignore
    await sess.flush()


async def _release_credit(
    sess: AsyncSession,
    row: models.GenerationCreditDay,
    hold_id: uuid.UUID,
) -> None:
    credits.release_generation_credit(row, hold_id)  # pyrefly: ignore
    await sess.flush()
