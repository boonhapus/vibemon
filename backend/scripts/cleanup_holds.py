"""Resolve stale generation holds and candidate review timeouts.

Usage: uv run --project backend python scripts/cleanup_holds.py [--db-path PATH]
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
import argparse
import datetime as dt
import pathlib
import sqlite3
import sys

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import models
from app.services.vibemon_service import VibemonService

_DEFAULT_DB = pathlib.Path(__file__).resolve().parent.parent.parent / ".scripts" / "vibemon.db"


@asynccontextmanager
async def database_session(db_path: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: sqlite3.Connection, _connection_record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as sess:
            yield sess
    finally:
        await engine.dispose()


async def run(db_path: str) -> int:
    now = dt.datetime.now(tz=dt.UTC)
    service = VibemonService(clock=lambda: now)
    async with database_session(db_path) as sess:
        timeout_count = await service.resolve_review_timeouts(sess)
        hold_count = await service.resolve_stale_holds(sess, timeout=dt.timedelta(minutes=10))
        await sess.commit()
    print(f"Resolved {timeout_count} timed-out reviews, {hold_count} stale holds.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve stale generation holds and review timeouts.")
    parser.add_argument("--db-path", type=str, default=_DEFAULT_DB.as_posix())
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    sys.exit(await run(db_path=args.db_path))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
