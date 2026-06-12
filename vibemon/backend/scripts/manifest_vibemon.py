"""Manifest christened Vibemons or reprocess transparent pose assets."""

from typing import Annotated
import asyncio
import uuid

import cyclopts
import sqlalchemy as sa
import structlog

from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import mapper, models, vibemon_repo
from app.workflows import asset_realization
from scripts import _common

_LOGGER = structlog.get_logger(__name__)

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)

app = cyclopts.App(
    help=(
        "Manifest christened Vibemon or reprocess stored sprites for transparency.\n\n"
        "Examples:\n"
        "  manifest_vibemon.py\n"
        "  manifest_vibemon.py --reprocess\n"
        "  manifest_vibemon.py --regenerate\n"
        "  manifest_vibemon.py --vibemon 019e8ddf-a63b-7340-8afd-d2e0289ffef9 --regenerate"
    )
)


@app.default
def manifest_vibemon(
    *,
    vibemon: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Specific Vibemon UUID; omitted selects all eligible."),
    ] = None,
    limit: Annotated[
        int | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Maximum Vibemon to process when none is selected."),
    ] = None,
    reprocess: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Re-chroma reference and poses from stored blobs (no GenAI). Use for manifested rows.",
        ),
    ] = False,
    regenerate: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Regenerate reference via GenAI and remanifest sprite sheet when present (costs credits).",
        ),
    ] = False,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Override database URL from the environment."),
    ] = None,
) -> None:
    """Run manifest or reprocess for eligible rows."""
    if regenerate and reprocess:
        raise ValueError("Use either --reprocess or --regenerate, not both.")
    settings = _common.load_script_settings(database_url=database_url)
    asyncio.run(
        _run_batch(
            settings.storage.database,
            vibemon_id=vibemon,
            limit=limit,
            reprocess=reprocess,
            regenerate=regenerate,
        )
    )


async def _run_batch(
    database_url: str,
    *,
    vibemon_id: uuid.UUID | None,
    limit: int | None,
    reprocess: bool,
    regenerate: bool,
) -> None:
    ok = 0
    failed = 0

    async with _common.session_scope(database_url=database_url) as sess:
        if reprocess or regenerate:
            lifecycles = (
                VibemonLifecycleT.CHRISTENED.value,
                VibemonLifecycleT.MANIFESTED.value,
            )
        else:
            lifecycles = (VibemonLifecycleT.CHRISTENED.value,)

        query = sa.select(models.Vibemon.id).where(models.Vibemon.lifecycle.in_(lifecycles)).order_by(models.Vibemon.id)
        if vibemon_id is not None:
            query = query.where(models.Vibemon.id == vibemon_id)
        if limit is not None:
            query = query.limit(limit)

        vibemon_ids = list((await sess.execute(query)).scalars().all())
        if not vibemon_ids:
            await _LOGGER.ainfo("No eligible Vibemon found", reprocess=reprocess, regenerate=regenerate)
            return

        await _LOGGER.ainfo(
            "Processing Vibemon batch",
            count=len(vibemon_ids),
            reprocess=reprocess,
            regenerate=regenerate,
        )
        for current_id in vibemon_ids:
            try:
                row = await vibemon_repo.load_vibemon(sess, current_id)
                vibemon = await mapper.vibemon_from_row(row)
                if regenerate:
                    vibemon = await asset_realization.regenerate_display_assets(vibemon)
                elif reprocess:
                    vibemon = await asset_realization.reprocess_display_assets(vibemon)
                else:
                    vibemon = await asset_realization.manifest_vibemon(vibemon)
                mapper.apply_vibemon_to_row(row, vibemon)
                await vibemon_repo.persist_assets(sess, vibemon)
                await sess.commit()
                ok += 1
                await _LOGGER.ainfo(
                    "Batch item complete",
                    vibemon_id=str(current_id),
                    name=vibemon.name,
                    lifecycle=vibemon.lifecycle.value,
                    reprocess=reprocess,
                    regenerate=regenerate,
                )
            except Exception as exc:
                await sess.rollback()
                failed += 1
                await _LOGGER.ainfo("Batch item failed", vibemon_id=str(current_id), error=str(exc))

    await _LOGGER.ainfo("Batch finished", ok=ok, failed=failed, reprocess=reprocess, regenerate=regenerate)


if __name__ == "__main__":
    app()
