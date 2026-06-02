"""Reusable database operations for Vibemon workflows."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.errors import CandidateReviewUnavailable
from app.core.ids import TrainerIdT
from app.domains.adoption import policy as adoption_policy
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.encounter.wild_encounter import EncounterCandidate, active_adjustment_multiplier
from app.domains.encounter.wild_pool import WildPoolCandidate, WildPoolService
from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.trainer import types as trainer_types
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.strength import member_strength
from app.providers import schema as providers_schema
from app.storage.blob import assets as blob_assets
from app.storage.database import mapper, models, move_catalog
from app.storage.secrets import repository as secrets_repository


async def persist_new_vibemon(
    sess: AsyncSession,
    *,
    vibemon: Vibemon,
    birth_seed: BirthSeed,
    snapshot: BirthSnapshot,
    now: dt.datetime,
) -> models.Vibemon:
    seed = models.BirthSeed(
        timestamp=birth_seed.timestamp,
        geo_coords=list(birth_seed.geo_coords),
        trainer_id=birth_seed.trainer_id,
    )
    snapshot_row = models.BirthSnapshot(birth_seed=seed, provider_payloads=snapshot.provider_payloads)
    row = models.Vibemon(
        id=vibemon.id,
        nickname=vibemon.nickname,
        xp=vibemon.xp,
        level=vibemon.level,
        evo_stage=int(vibemon.evo_stage),
        lifecycle=vibemon.lifecycle.value,
        disposition=None,
        team_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot_row,
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
    )
    row.identity = mapper.identity_row(vibemon)
    sess.add(row)
    await sess.flush()
    await persist_moves(sess, row, vibemon.moves, now=now)
    await persist_assets(sess, vibemon)
    return row


async def persist_moves(
    sess: AsyncSession,
    row: models.Vibemon,
    moves: tuple[Move, ...],
    *,
    now: dt.datetime,
) -> None:
    cache = await move_catalog.load_move_cache(sess)  # pyrefly: ignore

    for slot, move in enumerate(moves):
        move_row, created, _ = move_catalog.upsert_move(move, cache)  # pyrefly: ignore
        if created:
            sess.add(move_row)
            await sess.flush()
        sess.add(
            models.VibemonMove(
                vibemon_id=row.id,
                move_content_id=move_row.content_id,
                active_slot=slot,
            )
        )
        add_history(
            sess,
            row.id,
            VibemonHistoryEventT.MOVE_LEARNED,
            now,
            {
                "level": str(row.level),
                "move_content_id": move_row.content_id,
                "slot": str(slot),
                "source": "birth",
            },
        )


async def persist_assets(sess: AsyncSession, vibemon: Vibemon) -> None:
    if vibemon.aesthetic is None:
        return
    await blob_assets.upsert(sess, vibemon.id, vibemon.aesthetic.assets.values())


def create_review(
    vibemon_id: uuid.UUID,
    trainer_id: TrainerIdT,
    now: dt.datetime,
    *,
    timeout: dt.timedelta,
    provider_notes: tuple[providers_schema.ProviderNote, ...] = (),
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


async def set_trainer_lastfm_link(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    session_key: str | None,
    username: str | None,
) -> None:
    row = await sess.get(models.Trainer, trainer_id)
    if row is None:
        raise ValueError(f"Trainer {trainer_id} does not exist.")
    await secrets_repository.set_trainer_secret(sess, trainer_id, trainer_types.LASTFM_SESSION_KEY, session_key)
    await secrets_repository.set_trainer_secret(sess, trainer_id, trainer_types.LASTFM_USERNAME, username)


async def get_trainer_lastfm_link(sess: AsyncSession, trainer_id: uuid.UUID) -> tuple[str | None, str | None]:
    row = await sess.get(models.Trainer, trainer_id)
    if row is None:
        raise ValueError(f"Trainer {trainer_id} does not exist.")
    session_key = await secrets_repository.get_trainer_secret(sess, trainer_id, trainer_types.LASTFM_SESSION_KEY)
    username = await secrets_repository.get_trainer_secret(sess, trainer_id, trainer_types.LASTFM_USERNAME)
    return session_key, username


async def load_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> models.Vibemon:
    return (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(
                selectinload(models.Vibemon.identity),
                selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                selectinload(models.Vibemon.assets),
                selectinload(models.Vibemon.candidate_reviews),
            )
            .where(models.Vibemon.id == vibemon_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()


async def lock_trainer(sess: AsyncSession, trainer_id: TrainerIdT) -> None:
    await sess.execute(sa.select(models.Trainer.id).where(models.Trainer.id == trainer_id).with_for_update())


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


async def list_eligible_wild_ids(
    sess: AsyncSession,
    *,
    latitude: float,
    longitude: float,
    limit: int,
    wild_pool: WildPoolService | None = None,
) -> list[uuid.UUID]:
    rows = (
        await sess.execute(
            sa.select(models.Vibemon.id, models.BirthSeed.geo_coords)
            .join(models.BirthSnapshot, models.BirthSnapshot.id == models.Vibemon.birth_snapshot_id)
            .join(models.BirthSeed, models.BirthSeed.id == models.BirthSnapshot.birth_seed_id)
            .where(*eligible_wild_predicates())
            .order_by(models.Vibemon.wild_entered_at.desc().nullslast(), models.Vibemon.id)
        )
    ).all()
    candidates = [
        WildPoolCandidate(vibemon_id=vibemon_id, geo_coords=tuple(geo_coords)) for vibemon_id, geo_coords in rows
    ]
    return (wild_pool or WildPoolService()).select_eligible_wild_ids(
        candidates,
        latitude=latitude,
        longitude=longitude,
        limit=limit,
    )


async def load_encounter_candidates(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    eligible_ids: list[uuid.UUID],
    now: dt.datetime,
) -> list[EncounterCandidate]:
    adjustments = (
        await sess.execute(
            sa.select(models.EncounterAdjustment).where(
                models.EncounterAdjustment.trainer_id == trainer_id,
                models.EncounterAdjustment.vibemon_id.in_(eligible_ids),
            )
        )
    ).scalars()
    adjustment_by_vibemon = {row.vibemon_id: row for row in adjustments}

    rows = (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(selectinload(models.Vibemon.identity))
            .where(models.Vibemon.id.in_(eligible_ids))
        )
    ).scalars()
    out: list[EncounterCandidate] = []
    for row in rows:
        if row.identity is None:
            continue
        adjustment = adjustment_by_vibemon.get(row.id)
        out.append(
            EncounterCandidate(
                vibemon_id=row.id,
                member_strength=member_strength(row),  # pyrefly: ignore
                adjustment_multiplier=1.0
                if adjustment is None
                else active_adjustment_multiplier(
                    initial_multiplier=adjustment.initial_multiplier,
                    starts_at=adjustment.starts_at,
                    ends_at=adjustment.ends_at,
                    now=now,
                ),
            )
        )
    return out


async def is_wild_encounter_eligible(sess: AsyncSession, *, vibemon_id: uuid.UUID) -> bool:
    return (
        await sess.execute(
            sa.select(models.Vibemon.id).where(
                models.Vibemon.id == vibemon_id,
                *eligible_wild_predicates(),
            )
        )
    ).scalar_one_or_none() is not None


def eligible_wild_predicates() -> tuple[sa.ColumnElement[bool], ...]:
    pending_review_exists = sa.exists(
        sa.select(1).where(
            models.CandidateReview.vibemon_id == models.Vibemon.id,
            models.CandidateReview.status == CandidateReviewStatusT.PENDING.value,
        )
    )
    return (
        models.Vibemon.disposition == VibemonDispositionT.WILD.value,
        models.Vibemon.expired_at.is_(None),
        ~pending_review_exists,
    )


def add_history(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    event: VibemonHistoryEventT,
    occurred_at: dt.datetime,
    payload: dict[str, str],
) -> None:
    row = models.VibemonHistory(
        vibemon_id=vibemon_id,
        event_type=event.value,
        occurred_at=occurred_at,
        payload=payload,
    )
    sess.add(row)
