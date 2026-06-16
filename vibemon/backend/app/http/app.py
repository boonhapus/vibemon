"""Litestar application factory for the Vibemon game HTTP API."""

from app._compat.httpx import ensure_annotations
from app._compat.ssl import use_system_trust_store
from app._compat.warnings import suppress_third_party_warnings

suppress_third_party_warnings()
ensure_annotations()
use_system_trust_store()

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.di import Provide
from litestar.exceptions import ValidationException
from litestar.handlers.asgi_handlers import asgi
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core import logging as app_logging
from app.core.errors import VibemonServiceError
from app.http import deps, errors
from app.http.routes import assets, candidates, encounters, health, providers, trainers
from app.providers.music.lastfm import routes as lastfm_routes
from app.settings import Settings
from app.storage.database import engine as db_engine
from app.storage.database import models
from app.workflows.battle_play import BattleSessionRegistry

_lastfm_app = lastfm_routes.create_app()


@asgi("/lastfm", is_mount=True, copy_scope=False)
async def lastfm_mount(scope: Any, receive: Any, send: Any) -> None:
    await _lastfm_app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: Litestar) -> AsyncGenerator[None]:
    settings = Settings.load()
    db_engine.ensure_sqlite_parent_dir(settings.storage.database)
    engine = db_engine.create_async_database_engine(settings.storage.database)
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    app.state.engine = engine
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
    app.state.battle_session_registry = BattleSessionRegistry()
    try:
        yield
    finally:
        await engine.dispose()


def create_app() -> Litestar:
    settings = Settings.load()
    cors_origins = [
        "http://localhost:5173",
        "https://localhost:5173",
        "http://127.0.0.1:5173",
        "https://127.0.0.1:5173",
    ]

    return Litestar(
        route_handlers=[
            health.health_router,
            assets.assets_router,
            trainers.trainer_router,
            candidates.candidate_router,
            encounters.encounter_router,
            providers.provider_router,
            lastfm_mount,
        ],
        lifespan=[lifespan],
        dependencies={
            "db": Provide(deps.provide_db),
        },
        exception_handlers={
            ValidationException: errors.validation_exception_handler,
            VibemonServiceError: errors.service_exception_handler,
        },
        logging_config=app_logging.litestar_logging_config(),
        cors_config=CORSConfig(
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        ),
        debug=settings.environment == "dev",
    )


app = create_app()
