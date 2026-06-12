"""Redraw a pending candidate's display assets via GenAI."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.storage.database import candidate_review_repo, mapper, vibemon_repo
from app.workflows import asset_realization
from app.workflows.reference_facing import resolve_reference_facing


async def refresh_candidate_display_assets(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> str:
    """Regenerate the candidate's reference assets and return the refreshed facing."""
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    vibemon = await mapper.vibemon_from_row(review.vibemon)
    vibemon = await asset_realization.regenerate_display_assets(vibemon)
    mapper.apply_vibemon_to_row(review.vibemon, vibemon)
    await vibemon_repo.persist_assets(sess, vibemon)
    facing = resolve_reference_facing(vibemon)
    review.reference_facing = facing
    return facing
