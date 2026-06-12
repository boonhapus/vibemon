"""Wild Vibemon encounter lifecycle: pick → reveal → record → expire."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.core.errors import CandidateReviewUnavailable
from app.core.ids import TrainerIdT
from app.core.time import resolve_clock
from app.domains.encounter import tuning as encounter_tuning
from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.encounter.wild_encounter import (
    EncounterSelection,
    WildEncounterService,
)
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import history_repo, models, wild_pool_repo
from app.workflows import encounter_adjustment


async def pick_wild_encounter(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    latitude: float | None = None,
    longitude: float | None = None,
    crew_strength: float,
    desired_supply: int = 12,
) -> EncounterSelection | None:
    encounter_service = WildEncounterService()
    return await encounter_service.pick_encounter(
        trainer_id=trainer_id,
        latitude=latitude,
        longitude=longitude,
        crew_strength=crew_strength,
        list_eligible_wild_ids=lambda lat, lon, limit: wild_pool_repo.list_eligible_wild_ids(
            sess,
            latitude=lat,
            longitude=lon,
            limit=limit,
        ),
        load_candidates=lambda trainer, eligible_ids, now: wild_pool_repo.load_encounter_candidates(
            sess,
            trainer_id=trainer,
            eligible_ids=eligible_ids,
            now=now,
        ),
        revalidate_eligible=lambda vibemon_id: wild_pool_repo.is_wild_encounter_eligible(
            sess,
            vibemon_id=vibemon_id,
        ),
        desired_supply=desired_supply,
    )


async def record_wild_encounter_outcome(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    outcome: WildEncounterOutcomeT,
) -> None:
    now = resolve_clock()
    row = (
        await sess.execute(
            sa.select(models.Vibemon)
            .where(
                models.Vibemon.id == vibemon_id,
                models.Vibemon.disposition == VibemonDispositionT.WILD.value,
                models.Vibemon.expired_at.is_(None),
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise CandidateReviewUnavailable("Wild Vibemon is unavailable for encounter outcome.")
    row.last_encountered_at = now
    await encounter_adjustment.upsert_encounter_adjustment(sess, trainer_id, vibemon_id, outcome.value, now)
    history_repo.add_history(
        sess,
        vibemon_id,
        VibemonHistoryEventT.WILD_ENCOUNTER_COMPLETED,
        now,
        {"trainer_id": str(trainer_id), "outcome": outcome.value},
    )
    await sess.flush()


async def expire_wild(sess: AsyncSession) -> int:
    now = resolve_clock()
    threshold = now - encounter_tuning.WILD_EXPIRATION_WINDOW
    rows = (
        (
            await sess.execute(
                sa.select(models.Vibemon)
                .where(
                    models.Vibemon.disposition == VibemonDispositionT.WILD.value,
                    models.Vibemon.expired_at.is_(None),
                    sa.func.coalesce(
                        models.Vibemon.last_encountered_at,
                        models.Vibemon.wild_entered_at,
                    )
                    <= threshold,
                )
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.disposition = VibemonDispositionT.EXPIRED.value
        row.expired_at = now
        history_repo.add_history(sess, row.id, VibemonHistoryEventT.EXPIRED, now, {})
    await sess.flush()
    return len(rows)
