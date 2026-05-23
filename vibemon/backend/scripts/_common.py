"""Shared command-line plumbing for thin Vibemon workflow scripts."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import dataclasses
import datetime as dt
import json
import os
import pathlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.ids import TrainerIdT
from app.domains.generation.seed import BirthSeed
from app.providers.climate.provider import ClimateProvider
from app.storage.database import models

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
_DEFAULT_GENERATED = _REPO_ROOT / ".generated"
_DEFAULT_DATABASE_PATH = _REPO_ROOT / ".generated" / "database" / "vibemon.sqlite"
DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{_DEFAULT_DATABASE_PATH.as_posix()}"
DEFAULT_ASSET_STORE_URL = f"file:///{(_DEFAULT_GENERATED / 'monstore').as_posix().lstrip('/')}"


def default_database_url() -> str:
    return os.getenv("VIBEMON_DATABASE_URL", DEFAULT_DATABASE_URL)


def parse_datetime(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def birth_seed(
    *,
    latitude: float,
    longitude: float,
    timestamp: str | None = None,
) -> BirthSeed:
    return BirthSeed(
        timestamp=parse_datetime(timestamp) if timestamp is not None else dt.datetime.now(tz=dt.UTC),
        geo_coords=(latitude, longitude),
        providers=[ClimateProvider()],
    )


@asynccontextmanager
async def session_scope(
    *,
    database_url: str,
    create_schema: bool = True,
) -> AsyncIterator[AsyncSession]:
    if database_url == DEFAULT_DATABASE_URL:
        _DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(database_url)
    try:
        if create_schema:
            async with engine.begin() as conn:
                await conn.run_sync(models.Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise
    finally:
        await engine.dispose()


def dump(value: object) -> None:
    if hasattr(value, "model_dump"):
        print(json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True))
        return
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = dataclasses.asdict(value)
    print(json.dumps(value, default=str, indent=2, sort_keys=True))


def trainer_id(value: uuid.UUID) -> TrainerIdT:
    return value


def ensure_local_blob_dir(url: str) -> None:
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme != "file":
        return
    raw = (parts.netloc + parts.path) if parts.netloc not in ("", "localhost") else parts.path
    stripped = raw.lstrip("/\\")
    path = pathlib.Path(stripped) if len(stripped) >= 2 and stripped[1] == ":" else pathlib.Path(raw)
    path.mkdir(parents=True, exist_ok=True)
