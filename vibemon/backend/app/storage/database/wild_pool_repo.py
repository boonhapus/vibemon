"""Wild pool eligibility queries and encounter candidate loading."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.ids import TrainerIdT
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.encounter.wild_encounter import EncounterCandidate, active_adjustment_multiplier
from app.domains.encounter.wild_pool import WildPoolCandidate, WildPoolService
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.strength import member_strength
from app.storage.database import models


async def list_eligible_wild_ids(
    sess: AsyncSession,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
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
    if latitude is None or longitude is None:
        return [candidate.vibemon_id for candidate in candidates[:limit]]
    return (wild_pool or WildPoolService()).select_eligible_wild_ids(
        candidates,
        latitude=latitude,
        longitude=longitude,
        limit=limit,
    )


async def count_eligible_wild_near(
    sess: AsyncSession,
    *,
    latitude: float,
    longitude: float,
) -> int:
    rows = (
        await sess.execute(
            sa.select(models.Vibemon.id, models.BirthSeed.geo_coords)
            .join(models.BirthSnapshot, models.BirthSnapshot.id == models.Vibemon.birth_snapshot_id)
            .join(models.BirthSeed, models.BirthSeed.id == models.BirthSnapshot.birth_seed_id)
            .where(*eligible_wild_predicates())
        )
    ).all()
    candidates = [
        WildPoolCandidate(vibemon_id=vibemon_id, geo_coords=tuple(geo_coords)) for vibemon_id, geo_coords in rows
    ]
    if not candidates:
        return 0
    return len(
        WildPoolService().select_eligible_wild_ids(
            candidates,
            latitude=latitude,
            longitude=longitude,
            limit=len(candidates),
        )
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


async def count_eligible_wild(sess: AsyncSession) -> int:
    return int(
        (
            await sess.execute(
                sa.select(sa.func.count()).select_from(models.Vibemon).where(*eligible_wild_predicates())
            )
        ).scalar_one()
    )


async def load_eligible_wild_summary(sess: AsyncSession) -> list[tuple[int, list[str]]]:
    rows = (
        await sess.execute(
            sa.select(models.Vibemon.level, models.Identity.elements)
            .join(models.Identity, models.Identity.vibemon_id == models.Vibemon.id)
            .where(*eligible_wild_predicates())
        )
    ).all()
    return [(int(level), list(elements)) for level, elements in rows]


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
