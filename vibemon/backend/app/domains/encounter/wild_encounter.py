"""Wild encounter selection with supply top-up and final eligibility revalidation."""

from collections.abc import Awaitable, Callable
import datetime as dt
import random
import uuid

from app.core.ids import TrainerIdT
from app.core.schema import FrozenSchema
from app.core.time import Clock, as_utc, resolve_clock
from app.domains.encounter import tuning as encounter_tuning

type EligibleWildLister = Callable[[float | None, float | None, int], Awaitable[list[uuid.UUID]]]
type EncounterCandidateLoader = Callable[
    [TrainerIdT, list[uuid.UUID], dt.datetime], Awaitable[list["EncounterCandidate"]]
]
type EncounterEligibilityChecker = Callable[[uuid.UUID], Awaitable[bool]]
type WildSupplyGenerator = Callable[[float, float], Awaitable[uuid.UUID]]
type EncounterRevealHook = Callable[[uuid.UUID], Awaitable[None]]


class EncounterSelection(FrozenSchema):
    vibemon_id: uuid.UUID
    weight: float


class EncounterCandidate(FrozenSchema):
    vibemon_id: uuid.UUID
    member_strength: float
    adjustment_multiplier: float = 1.0


class WildEncounterService:
    def __init__(
        self,
        *,
        clock: Clock | None = None,
        rng: random.Random | None = None,
        supply_generator: WildSupplyGenerator | None = None,
        reveal_hook: EncounterRevealHook | None = None,
    ) -> None:
        self._clock = clock
        self._rng = rng or random.Random()
        self._supply_generator = supply_generator
        self._reveal_hook = reveal_hook

    async def pick_encounter(
        self,
        *,
        trainer_id: TrainerIdT,
        latitude: float | None,
        longitude: float | None,
        crew_strength: float,
        list_eligible_wild_ids: EligibleWildLister,
        load_candidates: EncounterCandidateLoader,
        revalidate_eligible: EncounterEligibilityChecker,
        desired_supply: int = 12,
    ) -> EncounterSelection | None:
        eligible_ids = await list_eligible_wild_ids(latitude, longitude, max(desired_supply, 1))
        if len(eligible_ids) < desired_supply and self._supply_generator is not None:
            missing = desired_supply - len(eligible_ids)
            for _ in range(missing):
                await self._supply_generator(latitude or 0.0, longitude or 0.0)
            eligible_ids = await list_eligible_wild_ids(latitude, longitude, desired_supply)
        if not eligible_ids:
            return None

        candidates = await load_candidates(trainer_id, eligible_ids, self._now())
        if not candidates:
            return None

        target = max(crew_strength * encounter_tuning.WILD_TARGET_RATIO, 1.0)
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
            if await revalidate_eligible(chosen_id):
                if self._reveal_hook is not None:
                    await self._reveal_hook(chosen_id)
                return EncounterSelection(vibemon_id=chosen_id, weight=chosen_weight)
            weighted = [(vibemon_id, weight) for vibemon_id, weight in weighted if vibemon_id != chosen_id]
        return None

    def _encounter_weight(self, candidate: EncounterCandidate, *, target: float, lower: float, upper: float) -> float:
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
        return resolve_clock(self._clock)


def active_adjustment_multiplier(
    *,
    initial_multiplier: float,
    starts_at: dt.datetime,
    ends_at: dt.datetime,
    now: dt.datetime,
) -> float:
    starts_at = as_utc(starts_at)
    ends_at = as_utc(ends_at)
    if now >= ends_at:
        return 1.0
    total = (ends_at - starts_at).total_seconds()
    if total <= 0:
        return 1.0
    elapsed = max((now - starts_at).total_seconds(), 0.0)
    progress = min(elapsed / total, 1.0)
    return initial_multiplier + ((1.0 - initial_multiplier) * progress)


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
