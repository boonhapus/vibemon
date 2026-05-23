"""Wild encounter selection with supply top-up and final eligibility revalidation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import datetime as dt
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app import models, types
from app.balance.strength import member_strength
from app.services import encounter_tuning
from app.services.wild_pool import WildPoolService

type Clock = Callable[[], dt.datetime]
type WildSupplyGenerator = Callable[[AsyncSession, float, float], Awaitable[uuid.UUID]]
type EncounterRevealHook = Callable[[AsyncSession, uuid.UUID], Awaitable[None]]


@dataclass(frozen=True)
class EncounterSelection:
    vibemon_id: uuid.UUID
    weight: float


class WildEncounterService:
    def __init__(
        self,
        *,
        wild_pool: WildPoolService | None = None,
        clock: Clock | None = None,
        rng: random.Random | None = None,
        supply_generator: WildSupplyGenerator | None = None,
        reveal_hook: EncounterRevealHook | None = None,
    ) -> None:
        self._wild_pool = wild_pool or WildPoolService()
        self._clock = clock or (lambda: dt.datetime.now(tz=dt.UTC))
        self._rng = rng or random.Random()
        self._supply_generator = supply_generator
        self._reveal_hook = reveal_hook

    async def pick_encounter(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        latitude: float,
        longitude: float,
        party_strength: float,
        desired_supply: int = 12,
    ) -> EncounterSelection | None:
        eligible_ids = await self._wild_pool.list_eligible_wild_ids(
            sess,
            latitude=latitude,
            longitude=longitude,
            limit=max(desired_supply, 1),
        )
        if len(eligible_ids) < desired_supply and self._supply_generator is not None:
            missing = desired_supply - len(eligible_ids)
            for _ in range(missing):
                await self._supply_generator(sess, latitude, longitude)
            eligible_ids = await self._wild_pool.list_eligible_wild_ids(
                sess,
                latitude=latitude,
                longitude=longitude,
                limit=desired_supply,
            )
        if not eligible_ids:
            return None

        candidates = await self._load_candidates(sess, trainer_id=trainer_id, eligible_ids=eligible_ids)
        if not candidates:
            return None

        target = max(party_strength * encounter_tuning.WILD_TARGET_RATIO, 1.0)
        lower = target * encounter_tuning.WILD_STRENGTH_BAND_MIN
        upper = target * encounter_tuning.WILD_STRENGTH_BAND_MAX
        in_band = [candidate for candidate in candidates if lower <= candidate.member_strength <= upper]
        pool = in_band if in_band else candidates
        prioritized = pool
        weighted = [
            (candidate.vibemon_id, self._encounter_weight(candidate, target=target, lower=lower, upper=upper))
            for candidate in prioritized
        ]

        while weighted:
            chosen_id, chosen_weight = _weighted_choice(weighted, rng=self._rng)
            if await self._revalidate_eligible(sess, vibemon_id=chosen_id):
                if self._reveal_hook is not None:
                    await self._reveal_hook(sess, chosen_id)
                return EncounterSelection(vibemon_id=chosen_id, weight=chosen_weight)
            weighted = [(vibemon_id, weight) for vibemon_id, weight in weighted if vibemon_id != chosen_id]
        return None

    async def _load_candidates(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        eligible_ids: list[uuid.UUID],
    ) -> list[_EncounterCandidate]:
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
        out: list[_EncounterCandidate] = []
        for row in rows:
            if row.identity is None:
                continue
            out.append(
                _EncounterCandidate(
                    vibemon_id=row.id,
                    member_strength=member_strength(row),
                    adjustment_multiplier=_active_adjustment_multiplier(
                        adjustment_by_vibemon.get(row.id),
                        now=self._now(),
                    ),
                )
            )
        return out

    async def _revalidate_eligible(self, sess: AsyncSession, *, vibemon_id: uuid.UUID) -> bool:
        pending_review_exists = sa.exists(
            sa.select(1).where(
                models.CandidateReview.vibemon_id == models.Vibemon.id,
                models.CandidateReview.status == types.CandidateReviewStatusT.PENDING.value,
            )
        )
        return (
            await sess.execute(
                sa.select(models.Vibemon.id).where(
                    models.Vibemon.id == vibemon_id,
                    models.Vibemon.disposition == types.VibemonDispositionT.WILD.value,
                    models.Vibemon.expired_at.is_(None),
                    ~pending_review_exists,
                )
            )
        ).scalar_one_or_none() is not None

    def _encounter_weight(self, candidate: _EncounterCandidate, *, target: float, lower: float, upper: float) -> float:
        if candidate.member_strength <= lower:
            strength_weight = max(candidate.member_strength / max(lower, 1.0), 0.0)
        elif candidate.member_strength >= upper:
            strength_weight = max(upper / max(candidate.member_strength, 1.0), 0.0)
        else:
            spread = max(upper - lower, 1.0)
            delta = abs(candidate.member_strength - target)
            strength_weight = max(1.0 - (delta / spread), 0.0)
        return strength_weight * candidate.adjustment_multiplier

    def _now(self) -> dt.datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=dt.UTC)
        return now.astimezone(dt.UTC)


@dataclass(frozen=True)
class _EncounterCandidate:
    vibemon_id: uuid.UUID
    member_strength: float
    adjustment_multiplier: float


def _active_adjustment_multiplier(adjustment: models.EncounterAdjustment | None, *, now: dt.datetime) -> float:
    if adjustment is None:
        return 1.0
    starts_at = _utc(adjustment.starts_at)
    ends_at = _utc(adjustment.ends_at)
    if now >= ends_at:
        return 1.0
    total = (ends_at - starts_at).total_seconds()
    if total <= 0:
        return 1.0
    elapsed = max((now - starts_at).total_seconds(), 0.0)
    progress = min(elapsed / total, 1.0)
    return adjustment.initial_multiplier + ((1.0 - adjustment.initial_multiplier) * progress)


def _weighted_choice(candidates: list[tuple[uuid.UUID, float]], *, rng: random.Random) -> tuple[uuid.UUID, float]:
    positive = [(vibemon_id, weight) for vibemon_id, weight in candidates if weight > 0]
    if positive:
        candidates = positive
    total = sum(max(weight, 0.0) for _, weight in candidates)
    if total <= 0:
        return rng.choice(candidates)
    point = rng.random() * total
    current = 0.0
    for vibemon_id, weight in candidates:
        current += max(weight, 0.0)
        if point <= current:
            return vibemon_id, weight
    return candidates[-1]


def _utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)
