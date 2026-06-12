"""Wild disposition transitions for candidates and released crew members."""

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import history_repo, models
from app.workflows.encounter_adjustment import upsert_encounter_adjustment


async def resolve_candidate_to_wild(
    sess: AsyncSession,
    review: models.CandidateReview,
    now: dt.datetime,
    *,
    status: CandidateReviewStatusT,
    event: VibemonHistoryEventT,
) -> None:
    review.status = status.value
    review.resolution = status.value
    review.resolved_at = now
    mark_wild(review.vibemon, now)
    await upsert_encounter_adjustment(sess, review.trainer_id, review.vibemon_id, status.value, now)
    history_repo.add_history(sess, review.vibemon_id, event, now, {"trainer_id": str(review.trainer_id)})


def mark_wild(row: models.Vibemon, now: dt.datetime) -> None:
    row.trainer_id = None
    row.crew_slot = None
    row.disposition = VibemonDispositionT.WILD.value
    row.wild_entered_at = now
    row.last_encountered_at = now


def release_to_wild(
    sess: AsyncSession,
    row: models.Vibemon,
    trainer_id: TrainerIdT,
    now: dt.datetime,
) -> None:
    mark_wild(row, now)
    history_repo.add_history(sess, row.id, VibemonHistoryEventT.RELEASED, now, {"trainer_id": str(trainer_id)})
