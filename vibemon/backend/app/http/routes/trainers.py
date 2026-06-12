"""Trainer registration, session, and onboarding routes."""

from dataclasses import dataclass
from typing import Annotated
import uuid

from litestar import Response, Router, get, post, put
from litestar.connection import Request
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import ClientException, HTTPException, NotFoundException
from litestar.params import Body
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.trainer import assets as trainer_assets
from app.domains.trainer import crew
from app.domains.trainer import schema as trainer_schema
from app.domains.vibemon.disposition import VibemonDispositionT
from app.genai import vibemon_assets
from app.http import deps
from app.http.schemas import TrainerUsernameBody, UsernameAvailabilityRead
from app.http.schemas import crew as crew_schemas
from app.storage.blob.monstore import MonStore, get_default_monstore
from app.storage.database import mapper, models, read_model, trainer_repo
from app.workflows import public_projection, trainer_reference

_REFERENCE_MEDIA_BY_SUFFIX = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}


@dataclass
class TrainerReferenceUpload:
    image: UploadFile


def _session_response(
    request: Request,
    payload: trainer_schema.PublicTrainerRead,
) -> Response[trainer_schema.PublicTrainerRead]:
    r = Response(content=payload)
    r.set_cookie(
        key=deps.SESSION_COOKIE,
        value=str(payload.id),
        max_age=deps.session_max_age_s(),
        httponly=True,
        samesite="lax",
        secure=deps.session_secure(),
        path="/",
    )
    return r


async def _trainer_reference_asset(db: AsyncSession, trainer_id: uuid.UUID) -> models.TrainerAsset | None:
    return (
        await db.execute(
            sa.select(models.TrainerAsset).where(
                models.TrainerAsset.trainer_id == trainer_id,
                models.TrainerAsset.kind == trainer_assets.TrainerAssetKind.REFERENCE.value,
            )
        )
    ).scalar_one_or_none()


async def _public_trainer_read(
    trainer: models.Trainer,
    db: AsyncSession,
    *,
    monstore: MonStore | None = None,
) -> trainer_schema.PublicTrainerRead:
    asset_store = monstore or get_default_monstore()
    crew_count = await trainer_repo.count_owned_vibemons(db, trainer.id)
    reference = await _trainer_reference_asset(db, trainer.id)
    reference_url = asset_store.http_asset_url(reference.object_key) if reference is not None else None
    return trainer_schema.PublicTrainerRead(
        id=trainer.id,
        username=trainer.username,
        crew_count=crew_count,
        reference_url=reference_url,
        reference_selected_revision=reference.selected_revision if reference is not None else None,
        reference_max_revision=reference.max_revision if reference is not None else None,
    )


def _reference_media_type(upload: UploadFile) -> str:
    if upload.content_type in vibemon_assets.REFERENCE_LIKENESS_MEDIA:
        return upload.content_type
    filename = upload.filename or ""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in _REFERENCE_MEDIA_BY_SUFFIX:
        return _REFERENCE_MEDIA_BY_SUFFIX[suffix]
    raise ClientException(detail="Reference upload must be a PNG, JPEG, or WebP image.")


@post("/check-username")
async def check_username(
    data: TrainerUsernameBody,
    db: AsyncSession,
) -> UsernameAvailabilityRead:
    """Return whether a username is free to register."""
    t = await trainer_repo.get_trainer_by_username(db, data.username)
    if t is None:
        return UsernameAvailabilityRead(available=True)
    return UsernameAvailabilityRead(
        available=False,
        detail="That username is already taken.",
    )


@post("/login")
async def login(
    request: Request,
    data: TrainerUsernameBody,
    db: AsyncSession,
) -> Response[trainer_schema.PublicTrainerRead]:
    """Sign in with a username and start a session."""
    if (t := await trainer_repo.get_trainer_by_username(db, data.username)) is None:
        raise NotFoundException(detail="No Trainer found with that name.")

    return _session_response(request, await _public_trainer_read(t, db))


@post("/logout")
async def logout(request: Request) -> Response[None]:
    """Clear the session cookie."""
    r = Response(content=None, status_code=204)
    r.delete_cookie(key=deps.SESSION_COOKIE, path="/")
    return r


@get("/me")
async def me(
    request: Request,
    db: AsyncSession,
) -> trainer_schema.PublicTrainerRead:
    """Return the signed-in trainer."""
    t = await deps.load_authenticated_trainer(request, db)
    return await _public_trainer_read(t, db)


@post("/register")
async def register(
    request: Request,
    data: TrainerUsernameBody,
    db: AsyncSession,
) -> Response[trainer_schema.PublicTrainerRead]:
    """Create a trainer account and start a session."""
    t = models.Trainer(id=uuid.uuid7(), username=data.username)
    db.add(t)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=HTTP_409_CONFLICT,
            detail="That username is already taken.",
        ) from exc

    return _session_response(request, await _public_trainer_read(t, db))


@post("/reference")
async def upload_reference(
    request: Request,
    data: Annotated[TrainerReferenceUpload, Body(media_type=RequestEncodingType.MULTI_PART)],
    db: AsyncSession,
) -> trainer_schema.PublicTrainerRead:
    """Generate and store a styled trainer reference from an uploaded likeness photo."""
    trainer = await deps.load_authenticated_trainer(request, db)
    likeness = await data.image.read()
    media_type = _reference_media_type(data.image)

    try:
        await trainer_reference.upload_trainer_reference(
            db,
            trainer,
            likeness=likeness,
            media_type=media_type,
        )
    except ValueError as exc:
        raise ClientException(detail=str(exc)) from exc

    await db.commit()
    return await _public_trainer_read(trainer, db)


async def _crew_list_read(db: AsyncSession, trainer_id: uuid.UUID) -> crew_schemas.CrewListRead:
    rows = await trainer_repo.load_owned_vibemons(db, trainer_id)
    assembler = read_model.ReadModelAssembler(
        schema_loader=mapper.vibemon_from_row,
        asset_urler=public_projection.default_asset_urler,
    )
    members = []
    for row in rows:
        public = await assembler.assemble(row, reviewing_trainer_id=trainer_id)
        members.append(crew_schemas.crew_member_read(public, reference_detected_facing=row.reference_detected_facing))
    return crew_schemas.CrewListRead(members=tuple(members))


@get("/crew")
async def list_crew(
    request: Request,
    db: AsyncSession,
) -> crew_schemas.CrewListRead:
    """Return owned Vibemon for the trainer party screen."""
    trainer = await deps.load_authenticated_trainer(request, db)
    return await _crew_list_read(db, trainer.id)


@put("/crew/order")
async def reorder_crew(
    request: Request,
    data: crew_schemas.CrewOrderWrite,
    db: AsyncSession,
) -> crew_schemas.CrewListRead:
    """Persist a new crew_slot assignment for every owned Vibemon."""
    trainer = await deps.load_authenticated_trainer(request, db)
    await trainer_repo.lock_trainer(db, trainer.id)
    rows = await trainer_repo.load_owned_vibemons(db, trainer.id)

    assignments = {entry.id: entry.crew_slot for entry in data.members}
    if len(assignments) != len(data.members):
        raise ClientException(detail="Duplicate Vibemon in crew order.")
    if assignments.keys() != {row.id for row in rows}:
        raise ClientException(detail="Crew order must include every owned Vibemon exactly once.")

    slots = list(assignments.values())
    if len(set(slots)) != len(slots) or any(slot < 0 or slot >= crew.MAX_CREW_SIZE for slot in slots):
        raise ClientException(detail="Crew slots must be unique and within the party range.")

    # The (trainer_id, crew_slot) unique index is enforced per row, so a cyclic
    # permutation cannot be applied in place. Vacate every slot first (the
    # disposition shape constraint requires clearing ownership alongside the
    # slot), then restore ownership with the new slots — all in one transaction.
    for row in rows:
        row.disposition = None
        row.trainer_id = None
        row.crew_slot = None
    await db.flush()
    for row in rows:
        row.disposition = VibemonDispositionT.OWNED.value
        row.trainer_id = trainer.id
        row.crew_slot = assignments[row.id]
    await db.commit()

    return await _crew_list_read(db, trainer.id)


trainer_router = Router(
    path="/api/trainers",
    route_handlers=[
        check_username,
        login,
        logout,
        me,
        register,
        upload_reference,
        list_crew,
        reorder_crew,
    ],
)
