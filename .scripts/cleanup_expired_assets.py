"""Delete retained assets for expired Vibemon.

Usage: uv run --project backend python .scripts/cleanup_expired_assets.py [--db-path PATH] [--days N] [--limit N]
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


async def run(db_path: str, *, days: int, limit: int | None) -> int:
    now = dt.datetime.now(tz=dt.UTC)
    service = VibemonService(clock=lambda: now)
    async with database_session(db_path) as sess:
        deleted_rows = await service.prune_expired_assets(
            sess,
            older_than=dt.timedelta(days=days),
            limit=limit,
        )
        await sess.commit()
    print(f"Deleted {deleted_rows} expired asset rows.")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete assets for expired Vibemon via retention workflow.")
    parser.add_argument("--db-path", type=str, default=_DEFAULT_DB.as_posix())
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help="Only clean assets for Vibemon expired at least N days ago.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max number of expired Vibemon to process.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    sys.exit(await run(db_path=args.db_path, days=args.days, limit=args.limit))


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
