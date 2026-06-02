"""Candidate Vibemon lifecycle: generate → adopt / reject."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.errors import CandidateReviewUnavailable, PartyFull
from app.core.ids import TrainerIdT
from app.core.time import resolve_clock
from app.domains.adoption import policy as adoption_policy
from app.domains.adoption.candidate import CANDIDATE_REVIEW_TIMEOUT
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.generation.seed import BirthSeed
from app.domains.trainer import credits, party
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import mapper, models, repositories
from app.workflows import _workflow_support as workflows
from app.workflows.materialize_vibemon import MaterializeVibemon


async def generate_candidate(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    birth_seed: BirthSeed,
    nickname: str | None = None,
    core_identity: str | None = None,
    bypass_credits: bool = False,
    christen: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    credit_day: models.GenerationCreditDay | None = None
    hold_id: uuid.UUID | None = None
    if not bypass_credits:
        credit_day, hold_id = await _reserve_credit(sess, trainer_id=trainer_id, now=now)
    try:
        row, provider_notes = await workflows.birth_and_persist_vibemon(
            sess,
            birth_seed=birth_seed,
            nickname=nickname,
            core_identity=core_identity,
            now=now,
            christen=christen,
        )
        review = repositories.create_review(
            row.id,
            trainer_id,
            now,
            timeout=CANDIDATE_REVIEW_TIMEOUT,
            provider_notes=provider_notes,
        )
        sess.add(review)
        repositories.add_history(
            sess,
            row.id,
            VibemonHistoryEventT.CANDIDATE_SHOWN,
            now,
            {"trainer_id": str(trainer_id)},
        )
        if credit_day is not None and hold_id is not None:
            await _consume_credit(sess, credit_day, hold_id)
        await sess.flush()
        loaded = await repositories.load_vibemon(sess, row.id)
        return await workflows.public_vibemon(loaded, reviewing_trainer_id=trainer_id)
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
    manifest: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    review = await repositories.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    if adoption_policy.review_deadline_passed(timeout_at=review.timeout_at, now=now):
        await workflows.resolve_candidate_to_wild(
            sess,
            review,
            now,
            status=CandidateReviewStatusT.TIMED_OUT,
            event=VibemonHistoryEventT.CANDIDATE_TIMED_OUT,
        )
        await sess.flush()
        raise CandidateReviewUnavailable("Candidate review has timed out.")

    plan = await _adoption_plan(sess, trainer_id=trainer_id, release_vibemon_id=release_vibemon_id)
    vibemon = await mapper.vibemon_from_row(review.vibemon)
    if manifest and vibemon.lifecycle is not VibemonLifecycleT.MANIFESTED:
        vibemon = await MaterializeVibemon().manifest(vibemon)

    if plan.release is not None:
        workflows.release_to_wild(sess, plan.release, trainer_id, now)
    mapper.apply_vibemon_to_row(review.vibemon, vibemon)
    review.vibemon.trainer_id = trainer_id
    review.vibemon.team_slot = plan.slot
    review.vibemon.disposition = VibemonDispositionT.OWNED.value
    review.vibemon.wild_entered_at = None
    review.vibemon.last_encountered_at = None
    review.status = CandidateReviewStatusT.ADOPTED.value
    review.resolution = CandidateReviewStatusT.ADOPTED.value
    review.resolved_at = now
    await repositories.persist_assets(sess, vibemon)
    repositories.add_history(
        sess,
        review.vibemon_id,
        VibemonHistoryEventT.CANDIDATE_ADOPTED,
        now,
        {"trainer_id": str(trainer_id)},
    )
    await sess.flush()
    loaded = await repositories.load_vibemon(sess, vibemon_id)
    return await workflows.public_vibemon(loaded, reviewing_trainer_id=trainer_id)


async def reject_candidate(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> PublicVibemon:
    now = resolve_clock()
    review = await repositories.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    await workflows.resolve_candidate_to_wild(
        sess,
        review,
        now,
        status=CandidateReviewStatusT.REJECTED,
        event=VibemonHistoryEventT.CANDIDATE_REJECTED,
    )
    await sess.flush()
    loaded = await repositories.load_vibemon(sess, vibemon_id)
    return await workflows.public_vibemon(loaded, reviewing_trainer_id=trainer_id)


class _AdoptionPlan:
    def __init__(self, *, slot: int, release: models.Vibemon | None) -> None:
        self.slot = slot
        self.release = release


async def _adoption_plan(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    release_vibemon_id: uuid.UUID | None,
) -> _AdoptionPlan:
    await repositories.lock_trainer(sess, trainer_id)
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
    used = {row.team_slot for row in rows if row.team_slot is not None}
    release = next((row for row in rows if row.id == release_vibemon_id), None) if release_vibemon_id else None
    release_slot = release.team_slot if release is not None else None
    slot = party.select_adoption_slot(
        owned_count=len(rows),
        used_slots=used,
        release_slot=release_slot,
    )
    if len(rows) >= party.MAX_PARTY_SIZE and release is None:
        raise PartyFull("Release Vibemon is not owned by this trainer.")
    return _AdoptionPlan(slot=slot, release=release if len(rows) >= party.MAX_PARTY_SIZE else None)


async def _reserve_credit(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    now: dt.datetime,
) -> tuple[models.GenerationCreditDay, uuid.UUID]:
    await repositories.lock_trainer(sess, trainer_id)
    row = await repositories.credit_day(sess, trainer_id=trainer_id, credit_date=now.date())
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
