"""Normalize trainer usernames and merge case-insensitive duplicates."""

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker
import cyclopts

from app.storage.database import engine as db_engine
from app.storage.database import repair as db_repair
from scripts import _common

app = cyclopts.App(
    help=(
        "Repair persisted trainer usernames.\n\n"
        "Examples:\n"
        "  repair_trainer_usernames.py"
    ),
    help_format="markdown",
)


@app.default
async def main(*, database_url: str | None = None) -> None:
    """Casefold usernames and merge trainers that differ only by casing."""
    settings = _common.load_script_settings(database_url=database_url)
    db_engine.ensure_sqlite_parent_dir(settings.storage.database)
    engine = db_engine.create_async_database_engine(settings.storage.database)
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            await db_repair.repair_trainer_usernames(db)
            await db.commit()
    finally:
        await engine.dispose()
    print(f"Repaired trainer usernames at {settings.storage.database}")


if __name__ == "__main__":
    asyncio.run(app())
