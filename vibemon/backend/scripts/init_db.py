"""Create Vibemon database tables from SQLAlchemy models."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
import cyclopts
import sqlalchemy as sa

from app.storage.blob.monstore import MonStore
from app.storage.bootstrap import seed_defaults
from app.storage.database import engine as db_engine
from app.storage.database import models
from scripts import _common

_PRESERVED_RESET_TABLES = frozenset(
    {
        models.Trainer.__table__,
        models.TrainerSecret.__table__,
    }
)


def _tables_to_drop_on_reset() -> list[sa.Table]:
    return [table for table in reversed(models.Base.metadata.sorted_tables) if table not in _PRESERVED_RESET_TABLES]


def _drop_reset_tables(sync_conn: sa.Connection) -> None:
    models.Base.metadata.drop_all(sync_conn, tables=_tables_to_drop_on_reset())


app = cyclopts.App(
    help=("Initialize the Vibemon database schema.\n\nExamples:\n  init_db.py\n  init_db.py --reset"),
    help_format="markdown",
)


@app.default
async def main(
    *,
    reset: bool = False,
    database_url: str | None = None,
) -> None:
    """Create all tables on the configured database (idempotent on a fresh DB)."""
    storage = _common.load_script_settings(database_url=database_url)
    db_engine.ensure_sqlite_parent_dir(storage.storage.database)
    engine = db_engine.create_async_database_engine(storage.storage.database)
    monstore = MonStore(storage.storage.assets)
    try:
        async with engine.begin() as conn:
            if reset:
                await conn.run_sync(_drop_reset_tables)
            await conn.run_sync(models.Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as sess:
            seeded = await seed_defaults(sess, monstore=monstore)
            await sess.commit()
    finally:
        await engine.dispose()
    verb = "Reset" if reset else "Initialized"
    print(f"{verb} schema at {storage.storage.database}")
    print(f"Seeded monstore catalog defaults at {storage.storage.assets}")
    if not seeded:
        print("Canonical trainer reference already present; skipped rewrite.")


if __name__ == "__main__":
    asyncio.run(app())
