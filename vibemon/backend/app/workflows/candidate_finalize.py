"""Post-generate candidate review bookkeeping shared by HTTP and scripts."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.storage.database import candidate_review_repo, mapper, vibemon_repo
from app.workflows.reference_facing import resolve_reference_facing


async def record_candidate_review_facing(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> str:
    """Persist hatch UI facing on the pending review and vibemon row."""
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    facing = resolve_reference_facing(vibemon)
    review = await candidate_review_repo.pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    review.reference_facing = facing
    row.reference_detected_facing = (
        vibemon.reference_detected_facing.value if vibemon.reference_detected_facing else None
    )
    return facing
