"""Litestar dependency providers for database sessions and trainer auth."""

from collections.abc import AsyncGenerator
import uuid

from litestar.connection import ASGIConnection
from litestar.datastructures import State
from litestar.exceptions import NotAuthorizedException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.ids import TrainerIdT
from app.settings import Settings
from app.storage.database import models

SESSION_COOKIE = "vibemon_trainer"


def session_max_age_s() -> int:
    return 60 * 60 * 24 * 365


def session_secure() -> bool:
    return Settings.load().environment == "prod"


async def provide_db(state: State) -> AsyncGenerator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = state.session_factory
    async with factory() as db:
        yield db


def trainer_id_from_connection(connection: ASGIConnection) -> TrainerIdT | None:
    raw = connection.cookies.get(SESSION_COOKIE)
    if raw is None:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def require_trainer_id(connection: ASGIConnection) -> TrainerIdT:
    trainer_id = trainer_id_from_connection(connection)
    if trainer_id is None:
        raise NotAuthorizedException(detail="Sign in to continue.")
    return trainer_id


async def load_authenticated_trainer(
    connection: ASGIConnection,
    db: AsyncSession,
) -> models.Trainer:
    trainer_id = require_trainer_id(connection)
    row = await db.get(models.Trainer, trainer_id)
    if row is None:
        raise NotAuthorizedException(detail="Sign in to continue.")
    return row
