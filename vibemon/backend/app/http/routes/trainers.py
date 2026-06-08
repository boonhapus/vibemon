"""Trainer registration, session, and onboarding routes."""

from dataclasses import dataclass
from typing import Annotated
import uuid

from litestar import Response, Router, get, post
from litestar.connection import Request
from litestar.datastructures import UploadFile
from litestar.enums import RequestEncodingType
from litestar.exceptions import HTTPException, NotFoundException
from litestar.params import Body
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domains.trainer import schema as trainer_schema
from app.http import deps
from app.http.schemas import TrainerUsernameBody, UsernameAvailabilityRead
from app.storage.database import models, repositories

_LOGGER = structlog.get_logger(__name__)


@dataclass
class TrainerPortraitUpload:
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


@post("/check-username")
async def check_username(
    data: TrainerUsernameBody,
    db: AsyncSession,
) -> UsernameAvailabilityRead:
    """Return whether a username is free to register."""
    t = await repositories.get_trainer_by_username(db, data.username)
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
    if (t := await repositories.get_trainer_by_username(db, data.username)) is None:
        raise NotFoundException(detail="No Trainer found with that name.")

    n = await repositories.count_owned_vibemons(db, t.id)

    return _session_response(
        request,
        trainer_schema.PublicTrainerRead(id=t.id, username=t.username, crew_count=n),
    )


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
    n = await repositories.count_owned_vibemons(db, t.id)
    return trainer_schema.PublicTrainerRead(id=t.id, username=t.username, crew_count=n)


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

    return _session_response(
        request,
        trainer_schema.PublicTrainerRead(id=t.id, username=t.username, crew_count=0),
    )


@post("/portrait", status_code=204)
async def upload_portrait(
    data: Annotated[TrainerPortraitUpload, Body(media_type=RequestEncodingType.MULTI_PART)],
) -> None:
    """Accept a portrait image upload."""
    b = await data.image.read()
    _LOGGER.info("trainer_portrait_upload", size_bytes=len(b))


trainer_router = Router(
    path="/api/trainers",
    route_handlers=[
        check_username,
        login,
        logout,
        me,
        register,
        upload_portrait,
    ],
)
