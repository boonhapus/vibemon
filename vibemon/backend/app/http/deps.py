"""Litestar dependency providers for database sessions and trainer auth."""

from collections.abc import AsyncGenerator
import uuid

from litestar.connection import ASGIConnection, Request
from litestar.datastructures import State
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.http_handlers import HTTPRouteHandler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import BattleUnavailable
from app.core.ids import TrainerIdT
from app.settings import Settings
from app.storage.database import models
from app.workflows.battle_play import ActiveBattle, BattleSessionRegistry

SESSION_COOKIE = "vibemon_trainer"


def session_max_age_s() -> int:
    return 60 * 60 * 24 * 365


def session_secure() -> bool:
    return Settings.load().environment == "prod"


def dev_overrides_allowed() -> bool:
    """Whether local-only query flags and dev bypasses may take effect."""
    return Settings.load().environment != "prod"


async def provide_db(state: State) -> AsyncGenerator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = state.session_factory
    async with factory() as db:
        yield db


def trainer_id_from_connection(
    connection: ASGIConnection[HTTPRouteHandler, object, object, State],
) -> TrainerIdT | None:
    raw = connection.cookies.get(SESSION_COOKIE)
    if raw is None:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


def require_trainer_id(connection: ASGIConnection[HTTPRouteHandler, object, object, State]) -> TrainerIdT:
    trainer_id = trainer_id_from_connection(connection)
    if trainer_id is None:
        raise NotAuthorizedException(detail="Sign in to continue.")
    return trainer_id


async def load_authenticated_trainer(
    connection: ASGIConnection[HTTPRouteHandler, object, object, State],
    db: AsyncSession,
) -> models.Trainer:
    trainer_id = require_trainer_id(connection)
    row = await db.get(models.Trainer, trainer_id)
    if row is None:
        raise NotAuthorizedException(detail="Sign in to continue.")
    return row


def battle_session_registry(request: Request[object, object, State]) -> BattleSessionRegistry:
    return request.app.state.battle_session_registry


def load_battle_session(
    request: Request[object, object, State],
    *,
    battle_id: uuid.UUID,
    trainer_id: TrainerIdT,
) -> ActiveBattle:
    try:
        return request.app.state.battle_session_registry.get(battle_id, trainer_id=trainer_id)
    except BattleUnavailable as exc:
        raise NotAuthorizedException(detail=str(exc)) from exc
