"""Add reference-facing columns and backfill existing trainer and candidate rows."""

from typing import Annotated
import asyncio
import dataclasses
import uuid

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
import cyclopts
import sqlalchemy as sa
import structlog

from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets
from app.domains.trainer import const as trainer_const
from app.domains.vibemon.assets import AssetKind
from app.genai import vibemon_assets
from app.storage.blob.monstore import MonStore
from app.storage.database import engine as db_engine
from app.storage.database import models
from scripts import _common

_LOGGER = structlog.get_logger(__name__)

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

_REFERENCE_FACING_COLUMNS: tuple[tuple[str, str], ...] = (
    ("trainer", "reference_detected_facing"),
    ("vibemon", "reference_detected_facing"),
    ("candidate_review", "reference_facing"),
)

_DEFAULT_TRAINER_FACING = sprite_types.SpriteFacing.RIGHT
_CANONICAL_TRAINER_FACING = sprite_types.SpriteFacing.LEFT
_DEFAULT_CANDIDATE_FACING = sprite_types.SpriteFacing.LEFT.value.lower()


@dataclasses.dataclass(frozen=True)
class MigrationSummary:
    added_columns: tuple[str, ...]
    trainers_backfilled: int
    vibemons_backfilled: int
    candidate_reviews_backfilled: int


def _table_column_names(sync_conn: sa.Connection, table_name: str) -> set[str]:
    return {column["name"] for column in inspect(sync_conn).get_columns(table_name)}


async def _existing_column_names(conn: sa.Connection, table_name: str) -> set[str]:
    return await conn.run_sync(lambda sync_conn: _table_column_names(sync_conn, table_name))


async def _add_missing_columns(conn: sa.Connection) -> list[str]:
    added: list[str] = []
    for table_name, column_name in _REFERENCE_FACING_COLUMNS:
        columns = await _existing_column_names(conn, table_name)
        if column_name in columns:
            continue
        await conn.execute(sa.text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} VARCHAR"))
        added.append(f"{table_name}.{column_name}")
    return added


def _candidate_facing_label(facing: sprite_types.SpriteFacing | None) -> str:
    if facing is None:
        return _DEFAULT_CANDIDATE_FACING
    return facing.value.lower()


async def _load_trainer_reference_png(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    monstore: MonStore,
) -> bytes | None:
    row = (
        await sess.execute(
            sa.select(models.TrainerAsset).where(
                models.TrainerAsset.trainer_id == trainer_id,
                models.TrainerAsset.kind == trainer_assets.TrainerAssetKind.REFERENCE_RAW.value,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await sess.execute(
                sa.select(models.TrainerAsset).where(
                    models.TrainerAsset.trainer_id == trainer_id,
                    models.TrainerAsset.kind == trainer_assets.TrainerAssetKind.REFERENCE.value,
                )
            )
        ).scalar_one_or_none()
    if row is None or not await monstore.has(row.object_key):
        return None
    return await monstore.get(row.object_key)


async def _load_vibemon_reference_png(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    monstore: MonStore,
) -> bytes | None:
    row = (
        await sess.execute(
            sa.select(models.VibemonAsset).where(
                models.VibemonAsset.vibemon_id == vibemon_id,
                models.VibemonAsset.kind == AssetKind.REFERENCE_RAW.value,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = (
            await sess.execute(
                sa.select(models.VibemonAsset).where(
                    models.VibemonAsset.vibemon_id == vibemon_id,
                    models.VibemonAsset.kind == AssetKind.REFERENCE.value,
                )
            )
        ).scalar_one_or_none()
    if row is None or not await monstore.has(row.object_key):
        return None
    return await monstore.get(row.object_key)


async def _detect_trainer_facing(
    generator: vibemon_assets.VibemonAssetGenerator,
    reference_png: bytes,
) -> sprite_types.SpriteFacing:
    try:
        return await generator.detect_trainer_reference_facing(reference_png)
    except Exception as exc:
        await _LOGGER.awarn("trainer_reference_facing_detection_failed", error=str(exc))
        return _DEFAULT_TRAINER_FACING


async def _detect_vibemon_facing(
    generator: vibemon_assets.VibemonAssetGenerator,
    reference_png: bytes,
    *,
    vibemon_name: str,
) -> sprite_types.SpriteFacing:
    try:
        return await generator.detect_vibemon_reference_facing(
            reference_png,
            vibemon_name=vibemon_name,
        )
    except Exception as exc:
        await _LOGGER.awarn(
            "vibemon_reference_facing_detection_failed",
            vibemon=vibemon_name,
            error=str(exc),
        )
        return sprite_types.SpriteFacing.LEFT


async def _backfill_trainer_facing(
    sess: AsyncSession,
    *,
    monstore: MonStore,
    detect_facing: bool,
    generator: vibemon_assets.VibemonAssetGenerator | None,
) -> int:
    trainers = (
        (await sess.execute(sa.select(models.Trainer).where(models.Trainer.reference_detected_facing.is_(None))))
        .scalars()
        .all()
    )
    updated = 0
    for trainer in trainers:
        if trainer.id == trainer_const.CANONICAL_TRAINER_ID:
            trainer.reference_detected_facing = _CANONICAL_TRAINER_FACING.value
            updated += 1
            continue

        facing: sprite_types.SpriteFacing | None = None
        if detect_facing and generator is not None:
            reference_png = await _load_trainer_reference_png(sess, trainer.id, monstore=monstore)
            if reference_png is not None:
                facing = await _detect_trainer_facing(generator, reference_png)
        elif await _load_trainer_reference_png(sess, trainer.id, monstore=monstore) is not None:
            facing = _DEFAULT_TRAINER_FACING

        if facing is None:
            continue

        trainer.reference_detected_facing = facing.value
        updated += 1
    return updated


async def _backfill_vibemon_facing(
    sess: AsyncSession,
    *,
    monstore: MonStore,
    detect_facing: bool,
    generator: vibemon_assets.VibemonAssetGenerator | None,
) -> int:
    rows = (
        await sess.execute(
            sa.select(models.Vibemon, models.Identity)
            .join(models.Identity, models.Identity.vibemon_id == models.Vibemon.id)
            .where(models.Vibemon.reference_detected_facing.is_(None))
        )
    ).all()
    updated = 0
    for row, identity in rows:
        facing: sprite_types.SpriteFacing | None = None
        if detect_facing and generator is not None:
            reference_png = await _load_vibemon_reference_png(sess, row.id, monstore=monstore)
            if reference_png is not None:
                facing = await _detect_vibemon_facing(
                    generator,
                    reference_png,
                    vibemon_name=identity.name,
                )
        if facing is None:
            continue
        row.reference_detected_facing = facing.value
        updated += 1
    return updated


async def _backfill_candidate_review_facing(sess: AsyncSession) -> int:
    reviews = (
        await sess.execute(
            sa.select(models.CandidateReview, models.Vibemon)
            .join(models.Vibemon, models.Vibemon.id == models.CandidateReview.vibemon_id)
            .where(models.CandidateReview.reference_facing.is_(None))
        )
    ).all()
    updated = 0
    for review, vibemon_row in reviews:
        facing = (
            sprite_types.SpriteFacing(vibemon_row.reference_detected_facing)
            if vibemon_row.reference_detected_facing is not None
            else None
        )
        review.reference_facing = _candidate_facing_label(facing)
        updated += 1
    return updated


async def migrate_reference_facing(
    engine: AsyncEngine,
    *,
    monstore: MonStore,
    detect_facing: bool = False,
) -> MigrationSummary:
    generator = vibemon_assets.get_default_asset_generator() if detect_facing else None

    async with engine.begin() as conn:
        added_columns = await _add_missing_columns(conn)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as sess:
        trainers_backfilled = await _backfill_trainer_facing(
            sess,
            monstore=monstore,
            detect_facing=detect_facing,
            generator=generator,
        )
        vibemons_backfilled = await _backfill_vibemon_facing(
            sess,
            monstore=monstore,
            detect_facing=detect_facing,
            generator=generator,
        )
        candidate_reviews_backfilled = await _backfill_candidate_review_facing(sess)
        await sess.commit()

    return MigrationSummary(
        added_columns=tuple(added_columns),
        trainers_backfilled=trainers_backfilled,
        vibemons_backfilled=vibemons_backfilled,
        candidate_reviews_backfilled=candidate_reviews_backfilled,
    )


app = cyclopts.App(
    help=(
        "Add reference-facing columns and backfill trainer, Vibemon, and candidate rows.\n\n"
        "Examples:\n"
        "  migrate_candidate_reference_facing.py\n"
        "  migrate_candidate_reference_facing.py --detect-facing"
    ),
    help_format="markdown",
)


@app.default
async def main(
    *,
    detect_facing: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            negative="",
            help="Run GenAI facing detection on stored reference sprites before backfill.",
        ),
    ] = False,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Override VIBEMON_STORAGE__DATABASE."),
    ] = None,
) -> None:
    """Add missing columns and backfill reference-facing metadata."""
    storage = _common.load_script_settings(database_url=database_url)
    db_engine.ensure_sqlite_parent_dir(storage.storage.database)
    engine = db_engine.create_async_database_engine(storage.storage.database)
    monstore = MonStore(storage.storage.assets)
    try:
        summary = await migrate_reference_facing(
            engine,
            monstore=monstore,
            detect_facing=detect_facing,
        )
    finally:
        await engine.dispose()

    _common.dump(summary)
    if summary.added_columns:
        print(f"Added columns: {', '.join(summary.added_columns)}")
    print(
        "Backfilled "
        f"{summary.trainers_backfilled} trainer(s), "
        f"{summary.vibemons_backfilled} Vibemon(s), and "
        f"{summary.candidate_reviews_backfilled} candidate review(s)."
    )


if __name__ == "__main__":
    asyncio.run(app())
