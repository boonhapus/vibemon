"""Backfill vibemon_asset.display_anchor from stored reference display PNGs."""

from typing import Annotated
import asyncio
import dataclasses
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts
import sqlalchemy as sa
import structlog

from app.core.time import resolve_clock
from app.domains.vibemon.assets import AssetKind
from app.storage.blob.monstore import MonStore
from app.storage.database import models
from app.workflows import asset_realization
from scripts import _common

_LOGGER = structlog.get_logger(__name__)

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)


@dataclasses.dataclass(frozen=True)
class BackfillSummary:
    scanned: int
    updated: int
    skipped_missing_blob: int
    skipped_empty_sprite: int


async def backfill_display_anchors(
    sess: AsyncSession,
    *,
    monstore: MonStore,
    vibemon_id: uuid.UUID | None = None,
    limit: int | None = None,
    force: bool = False,
) -> BackfillSummary:
    query = sa.select(models.VibemonAsset).where(models.VibemonAsset.kind == AssetKind.REFERENCE.value)
    if not force:
        query = query.where(models.VibemonAsset.display_anchor.is_(None))
    if vibemon_id is not None:
        query = query.where(models.VibemonAsset.vibemon_id == vibemon_id)
    query = query.order_by(models.VibemonAsset.vibemon_id)
    if limit is not None:
        query = query.limit(limit)

    rows = list((await sess.execute(query)).scalars().all())
    updated = 0
    skipped_missing_blob = 0
    skipped_empty_sprite = 0
    now = resolve_clock()

    for row in rows:
        if not await monstore.has(row.object_key):
            skipped_missing_blob += 1
            await _LOGGER.awarn(
                "display_anchor_backfill_missing_blob",
                vibemon_id=str(row.vibemon_id),
                object_key=row.object_key,
            )
            continue

        png = await monstore.get(row.object_key)
        anchor = asset_realization.compute_display_anchor(png)
        if anchor is None:
            skipped_empty_sprite += 1
            continue

        row.display_anchor = anchor.model_dump()
        row.updated_at = now
        updated += 1

    if updated:
        await sess.commit()

    return BackfillSummary(
        scanned=len(rows),
        updated=updated,
        skipped_missing_blob=skipped_missing_blob,
        skipped_empty_sprite=skipped_empty_sprite,
    )


app = cyclopts.App(
    help=(
        "Compute display anchors for stored Vibemon reference sprites.\n\n"
        "Examples:\n"
        "  backfill_display_anchors.py\n"
        "  backfill_display_anchors.py --force\n"
        "  backfill_display_anchors.py --vibemon 019eb23d-32cc-722e-aba8-65bebac179de"
    ),
    help_format="markdown",
)


@app.default
async def main(
    *,
    vibemon: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Backfill one Vibemon; omitted selects all eligible rows."),
    ] = None,
    limit: Annotated[
        int | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Maximum reference rows to scan."),
    ] = None,
    force: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            negative="",
            help="Recompute anchors even when display_anchor is already set.",
        ),
    ] = False,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Override VIBEMON_STORAGE__DATABASE."),
    ] = None,
) -> None:
    """Alpha-scan reference display PNGs and persist feet anchors on vibemon_asset rows."""
    storage = _common.load_script_settings(database_url=database_url)
    monstore = MonStore(storage.storage.assets)
    async with _common.session_scope(database_url=storage.storage.database) as sess:
        summary = await backfill_display_anchors(
            sess,
            monstore=monstore,
            vibemon_id=vibemon,
            limit=limit,
            force=force,
        )

    _common.dump(summary)
    print(
        f"Scanned {summary.scanned} reference row(s); "
        f"updated {summary.updated}, "
        f"missing blob {summary.skipped_missing_blob}, "
        f"empty sprite {summary.skipped_empty_sprite}."
    )


if __name__ == "__main__":
    asyncio.run(app())
