"""Add ``growth_rate`` to existing databases and backfill birth rolls."""

import asyncio

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload
import cyclopts
import sqlalchemy as sa

from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.progression import formulas as progression_formulas
from app.domains.vibemon.types import EvolutionStageT
from app.storage.database import engine as db_engine
from app.storage.database import models
from scripts import _common

app = cyclopts.App(
    help=(
        "Migrate pre-progression databases so existing Vibemon can earn XP.\n\n"
        "Examples:\n"
        "  migrate_progression.py\n"
        "  migrate_progression.py --dry-run"
    ),
    help_format="markdown",
)


def _vibemon_column_names(sync_conn: sa.Connection) -> set[str]:
    return {column["name"] for column in inspect(sync_conn).get_columns("vibemon")}


async def _ensure_growth_rate_column(
    conn: sa.Connection,
    *,
    database_url: str,
    dry_run: bool,
) -> bool:
    columns = await conn.run_sync(_vibemon_column_names)
    if "growth_rate" in columns:
        return False

    if dry_run:
        print("Would add vibemon.growth_rate column.")
        return True

    if db_engine.is_postgres_url(database_url):
        await conn.execute(
            sa.text("ALTER TABLE vibemon ADD COLUMN IF NOT EXISTS growth_rate VARCHAR NOT NULL DEFAULT 'medium'")
        )
    else:
        await conn.execute(sa.text("ALTER TABLE vibemon ADD COLUMN growth_rate VARCHAR NOT NULL DEFAULT 'medium'"))
    await conn.commit()
    print("Added vibemon.growth_rate column.")
    return True


def _growth_rate_for_row(row: models.Vibemon) -> str:
    birth_seed_row = row.birth_snapshot.birth_seed
    seed = BirthSeed(
        timestamp=birth_seed_row.timestamp,
        geo_coords=tuple(birth_seed_row.geo_coords),
        trainer_id=birth_seed_row.trainer_id,
        providers=[],
    )
    elements = tuple(VibemonTypeT(element) for element in row.identity.elements)
    growth_rate = progression_formulas.roll_growth_rate(
        rng=seed.rng("identity.growth_rate"),
        evo_seed=EvolutionStageT(row.identity.evo_seed),
        elements=elements,
    )
    return growth_rate.value


@app.default
async def main(
    *,
    database_url: str | None = None,
    dry_run: bool = False,
) -> None:
    """Add ``growth_rate`` when missing and replay birth rolls for every Vibemon."""
    storage = _common.load_script_settings(database_url=database_url)
    db_engine.ensure_sqlite_parent_dir(storage.storage.database)
    engine = db_engine.create_async_database_engine(storage.storage.database)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with engine.connect() as conn:
            columns = await conn.run_sync(_vibemon_column_names)
            has_column = "growth_rate" in columns
            await _ensure_growth_rate_column(
                conn,
                database_url=storage.storage.database,
                dry_run=dry_run,
            )
            if dry_run and not has_column:
                count = (await conn.execute(sa.text("SELECT COUNT(*) FROM vibemon"))).scalar_one()
                print(f"Dry run: would backfill growth_rate for {count} Vibemon rows.")
                return

        async with session_factory() as sess:
            rows = (
                (
                    await sess.execute(
                        sa.select(models.Vibemon)
                        .options(
                            selectinload(models.Vibemon.identity),
                            selectinload(models.Vibemon.birth_snapshot).selectinload(models.BirthSnapshot.birth_seed),
                        )
                        .order_by(models.Vibemon.id)
                    )
                )
                .scalars()
                .all()
            )

            updated = 0
            for row in rows:
                replayed = _growth_rate_for_row(row)
                current = getattr(row, "growth_rate", None)
                if current == replayed:
                    continue
                updated += 1
                if dry_run:
                    print(f"Would set {row.id} growth_rate={replayed!r} (was {current!r})")
                    continue
                row.growth_rate = replayed

            if dry_run:
                print(f"Dry run: would update {updated} of {len(rows)} Vibemon rows.")
                return

            await sess.commit()
            print(f"Backfilled growth_rate on {updated} of {len(rows)} Vibemon rows.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(app())
