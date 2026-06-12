"""Assemble hatch review action payloads from persisted rows."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.domains.adoption import hatch_projection
from app.storage.database import candidate_review_repo, mapper, trainer_repo, vibemon_repo
from app.workflows import public_projection
from app.workflows import reference_facing as reference_facing_workflow


async def candidate_action_read(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    reference_facing: str | None = None,
) -> hatch_projection.CandidateActionRead:
    """Build the hatch UI payload for one candidate action response."""
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    public = await public_projection.public_vibemon(row, reviewing_trainer_id=trainer_id)
    crew_count = await trainer_repo.count_owned_vibemons(sess, trainer_id)

    if reference_facing is None:
        vibemon = await mapper.vibemon_from_row(row)
        review = await candidate_review_repo.load_pending_candidate_review(sess, trainer_id=trainer_id)
        if review is not None and review.vibemon_id == vibemon_id and review.reference_facing:
            reference_facing = review.reference_facing
        else:
            reference_facing = reference_facing_workflow.resolve_reference_facing(vibemon)

    return hatch_projection.CandidateActionRead(
        candidate=hatch_projection.assemble_hatch_candidate(public, reference_facing=reference_facing),
        crew_count=crew_count,
    )
