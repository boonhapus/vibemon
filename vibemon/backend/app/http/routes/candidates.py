"""Candidate generation and review routes for trainer onboarding."""

from typing import Annotated
import uuid

from litestar import Request, Response, Router, get, post
from litestar.background_tasks import BackgroundTask
from litestar.exceptions import ClientException
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domains.adoption import hatch_projection
from app.http import deps
from app.http.schemas import candidates as candidate_schemas
from app.storage.database import candidate_review_repo
from app.workflows import birth_seed as birth_seed_factory
from app.workflows import candidate as candidate_workflow


@get("/current")
async def current_candidate(
    request: Request,
    db: AsyncSession,
) -> hatch_projection.CandidateActionRead | None:
    """Return the trainer's pending candidate review, if any."""
    trainer = await deps.load_authenticated_trainer(request, db)
    review = await candidate_review_repo.load_pending_candidate_review(db, trainer_id=trainer.id)
    if review is None:
        return None
    return await candidate_workflow.candidate_action_read(
        db,
        trainer_id=trainer.id,
        vibemon_id=review.vibemon_id,
    )


@post("/generate")
async def generate_candidate(
    request: Request,
    data: candidate_schemas.CandidateGenerateBody,
    db: AsyncSession,
    bypass_credits: Annotated[bool, Parameter(query="bypass-credits")] = False,
) -> hatch_projection.CandidateActionRead:
    """Birth and christen a candidate from the trainer's enabled providers."""
    trainer = await deps.load_authenticated_trainer(request, db)
    if not data.providers:
        raise ClientException(detail="Enable at least one provider before hatching.")

    existing = await candidate_review_repo.load_pending_candidate_review(db, trainer_id=trainer.id)
    if existing is not None:
        raise ClientException(detail="Finish reviewing your current Vibemon before hatching another.")

    if bypass_credits and not deps.dev_overrides_allowed():
        raise ClientException(detail="Generation credit bypass is not available in production.")

    latitude, longitude = data.latitude, data.longitude
    if latitude is None or longitude is None:
        latitude, longitude = birth_seed_factory.default_coordinates()

    birth_seed = birth_seed_factory.build_birth_seed(
        trainer_id=trainer.id,
        latitude=latitude,
        longitude=longitude,
        provider_names=data.providers,
    )
    public = await candidate_workflow.generate_candidate(
        db,
        trainer_id=trainer.id,
        birth_seed=birth_seed,
        christen=True,
        bypass_credits=bypass_credits,
    )
    facing = await candidate_workflow.record_candidate_review_facing(
        db,
        trainer_id=trainer.id,
        vibemon_id=public.id,
    )
    await db.commit()
    return await candidate_workflow.candidate_action_read(
        db,
        trainer_id=trainer.id,
        vibemon_id=public.id,
        reference_facing=facing,
    )


@post("/{vibemon_id:uuid}/refresh")
async def refresh_candidate(
    vibemon_id: uuid.UUID,
    request: Request,
    db: AsyncSession,
) -> hatch_projection.CandidateActionRead:
    """Redraw the candidate's reference sprite via GenAI."""
    trainer = await deps.load_authenticated_trainer(request, db)
    facing = await candidate_workflow.refresh_candidate_display_assets(
        db,
        trainer_id=trainer.id,
        vibemon_id=vibemon_id,
    )
    await db.commit()
    return await candidate_workflow.candidate_action_read(
        db,
        trainer_id=trainer.id,
        vibemon_id=vibemon_id,
        reference_facing=facing,
    )


@post("/{vibemon_id:uuid}/reject")
async def reject_candidate(
    vibemon_id: uuid.UUID,
    request: Request,
    db: AsyncSession,
) -> None:
    """Release a pending candidate back to the wild supply."""
    trainer = await deps.load_authenticated_trainer(request, db)
    await candidate_workflow.reject_candidate(db, trainer_id=trainer.id, vibemon_id=vibemon_id)
    await db.commit()


@post("/{vibemon_id:uuid}/adopt")
async def adopt_candidate(
    vibemon_id: uuid.UUID,
    request: Request,
    data: candidate_schemas.CandidateAdoptBody,
    db: AsyncSession,
) -> Response[hatch_projection.CandidateActionRead]:
    """Adopt a pending candidate into the trainer crew."""
    trainer = await deps.load_authenticated_trainer(request, db)
    adopted = await candidate_workflow.adopt_candidate(
        db,
        trainer_id=trainer.id,
        vibemon_id=vibemon_id,
        nickname=data.nickname,
        manifest=False,
    )
    await db.commit()

    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    payload = await candidate_workflow.candidate_action_read(db, trainer_id=trainer.id, vibemon_id=adopted.id)
    return Response(
        content=payload,
        background=BackgroundTask(candidate_workflow.manifest_adopted_vibemon, vibemon_id, session_factory),
    )


candidate_router = Router(
    path="/api/candidates",
    route_handlers=[
        current_candidate,
        generate_candidate,
        refresh_candidate,
        reject_candidate,
        adopt_candidate,
    ],
)
