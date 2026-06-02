"""Async SQLAlchemy engine construction for app and script entrypoints."""

import pathlib

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def is_postgres_url(database_url: str) -> bool:
    return database_url.startswith("postgresql")


def is_sqlite_url(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def create_async_database_engine(database_url: str, *, echo: bool = False) -> AsyncEngine:
    kwargs: dict[str, object] = {"echo": echo}
    if is_postgres_url(database_url):
        kwargs.update(pool_size=10, max_overflow=20, pool_pre_ping=True)
    return create_async_engine(database_url, **kwargs)


def ensure_sqlite_parent_dir(database_url: str) -> None:
    if not is_sqlite_url(database_url):
        return
    if database_url.endswith(":memory:"):
        return
    path_part = database_url.split("///", maxsplit=1)[-1]
    pathlib.Path(path_part).parent.mkdir(parents=True, exist_ok=True)
