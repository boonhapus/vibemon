"""Regenerate or reprocess trainer reference sprites.

``--regenerate`` re-runs GenAI from a likeness photo (costs credits) and is the
trainer analogue of re-rolling a look. ``--reprocess`` re-keys and re-snaps the
display sprite from the stored ``REFERENCE_RAW`` blob with no GenAI call — use it
after changing the trainer post-processing pipeline.
"""

from typing import Annotated
import asyncio
import io
import pathlib
import uuid

from PIL import Image
import cyclopts
import numpy as np
import sqlalchemy as sa
import structlog

from app.domains.sprite import const as sprite_const
from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets
from app.domains.vibemon.brand import Color
from app.storage.blob import assets as blob_assets
from app.storage.blob.monstore import MonStore, get_default_monstore
from app.storage.database import models
from app.workflows import sprite_postprocess, trainer_reference
from scripts import _common

_LOGGER = structlog.get_logger(__name__)

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

_MEDIA_BY_SUFFIX = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}

app = cyclopts.App(
    help=(
        "Regenerate or reprocess trainer reference sprites.\n\n"
        "Pass exactly one mode:\n"
        "  --reprocess   re-key and re-snap the display from the stored REFERENCE_RAW (no GenAI).\n"
        "  --regenerate  re-run GenAI from a likeness photo (costs credits; single trainer).\n\n"
        "Examples:\n"
        "  generate_trainer.py --reprocess\n"
        "  generate_trainer.py --trainer 019eb9de-493f-7180-a207-e3834f0611fc --reprocess\n"
        "  generate_trainer.py --trainer 019eb9de-493f-7180-a207-e3834f0611fc "
        "--likeness ./me.png --regenerate"
    )
)


@app.default
def generate_trainer(
    *,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Specific trainer UUID; omitted selects all eligible (reprocess).",
        ),
    ] = None,
    likeness: Annotated[
        pathlib.Path | None,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Likeness photo path; required for --regenerate (PNG/JPEG/WebP).",
        ),
    ] = None,
    reprocess: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Re-key and re-snap the display from the stored REFERENCE_RAW (no GenAI).",
        ),
    ] = False,
    regenerate: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Re-run GenAI from --likeness and persist a fresh reference revision (costs credits).",
        ),
    ] = False,
    limit: Annotated[
        int | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Maximum trainers to process when none is selected."),
    ] = None,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
    asset_store_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Asset store URL override; defaults to VIBEMON_STORAGE__ASSETS.",
        ),
    ] = None,
    bust_cache: Annotated[bool, _common.bust_cache_parameter(ADVANCED_OPTIONS)] = False,
) -> None:
    """Run reprocess or regenerate for eligible trainer references."""
    if regenerate and reprocess:
        raise SystemExit("Use either --reprocess or --regenerate, not both.")
    if not regenerate and not reprocess:
        raise SystemExit("Pass --reprocess (re-key stored raw) or --regenerate (GenAI from --likeness).")
    if regenerate and trainer is None:
        raise SystemExit("--regenerate requires --trainer <uuid>.")
    if regenerate and likeness is None:
        raise SystemExit("--regenerate requires --likeness <path>; the original photo is not stored.")
    if reprocess and likeness is not None:
        raise SystemExit("--likeness is only used with --regenerate.")

    settings = _common.load_script_settings(
        database_url=database_url,
        asset_store_url=asset_store_url,
        bust_cache=bust_cache,
    )
    asyncio.run(
        _run_batch(
            settings.storage.database,
            settings.storage.assets,
            trainer_id=trainer,
            likeness=likeness,
            limit=limit,
            reprocess=reprocess,
            regenerate=regenerate,
        )
    )


async def _run_batch(
    database_url: str,
    asset_store_url: str,
    *,
    trainer_id: uuid.UUID | None,
    likeness: pathlib.Path | None,
    limit: int | None,
    reprocess: bool,
    regenerate: bool,
) -> None:
    _common.ensure_local_blob_dir(asset_store_url)
    monstore = get_default_monstore()
    likeness_bytes, media_type = _read_likeness(likeness) if regenerate else (None, None)

    ok = 0
    failed = 0
    async with _common.session_scope(database_url=database_url) as sess:
        trainer_ids = await _eligible_trainer_ids(sess, trainer_id=trainer_id, limit=limit)
        if not trainer_ids:
            await _LOGGER.ainfo("No eligible trainers found", reprocess=reprocess, regenerate=regenerate)
            return

        await _LOGGER.ainfo(
            "Processing trainer batch",
            count=len(trainer_ids),
            reprocess=reprocess,
            regenerate=regenerate,
        )
        for current_id in trainer_ids:
            try:
                trainer = await sess.get(models.Trainer, current_id)
                if trainer is None:
                    raise ValueError("trainer row not found")
                if regenerate:
                    assert likeness_bytes is not None
                    assert media_type is not None
                    facing = await trainer_reference.upload_trainer_reference(
                        sess,
                        trainer,
                        likeness=likeness_bytes,
                        media_type=media_type,
                    )
                else:
                    facing = await _reprocess_one(sess, trainer, monstore=monstore)
                await sess.commit()
                ok += 1
                await _LOGGER.ainfo(
                    "Trainer reference updated",
                    trainer_id=str(current_id),
                    username=trainer.username,
                    facing=facing.value,
                    reprocess=reprocess,
                    regenerate=regenerate,
                )
            except Exception as exc:
                await sess.rollback()
                failed += 1
                await _LOGGER.ainfo("Trainer reference failed", trainer_id=str(current_id), error=str(exc))

    await _LOGGER.ainfo("Batch finished", ok=ok, failed=failed, reprocess=reprocess, regenerate=regenerate)


async def _eligible_trainer_ids(
    sess: object,
    *,
    trainer_id: uuid.UUID | None,
    limit: int | None,
) -> list[uuid.UUID]:
    if trainer_id is not None:
        return [trainer_id]

    query = (
        sa.select(models.TrainerAsset.trainer_id)
        .where(models.TrainerAsset.kind == trainer_assets.TrainerAssetKind.REFERENCE_RAW.value)
        .order_by(models.TrainerAsset.trainer_id)
    )
    if limit is not None:
        query = query.limit(limit)
    return list((await sess.execute(query)).scalars().all())  # type: ignore[attr-defined]


async def _reprocess_one(
    sess: object,
    trainer: models.Trainer,
    *,
    monstore: MonStore,
) -> sprite_types.SpriteFacing:
    raw_row = (
        await sess.execute(  # type: ignore[attr-defined]
            sa.select(models.TrainerAsset).where(
                models.TrainerAsset.trainer_id == trainer.id,
                models.TrainerAsset.kind == trainer_assets.TrainerAssetKind.REFERENCE_RAW.value,
            )
        )
    ).scalar_one_or_none()
    if raw_row is None:
        raise ValueError("trainer has no REFERENCE_RAW to reprocess")

    raw_key = monstore.trainer_asset_key(
        trainer.id,
        trainer_assets.TrainerAssetKind.REFERENCE_RAW,
        raw_row.selected_revision,
    )
    raw = await monstore.get(raw_key)

    bg_color = _detect_reference_matte(raw)
    normalized = sprite_postprocess.normalize_trainer_reference_image(raw, bg_color=bg_color)
    facing = (
        sprite_types.SpriteFacing(trainer.reference_detected_facing)
        if trainer.reference_detected_facing
        else sprite_types.SpriteFacing.RIGHT
    )
    display = sprite_postprocess.finalize_reference_display(
        normalized,
        facing=facing,
        profile=sprite_const.TRAINER_REFERENCE_SNAP,
    )
    await blob_assets.append_trainer_asset(
        sess,  # type: ignore[arg-type]
        trainer.id,
        trainer_assets.TrainerAssetKind.REFERENCE,
        display,
        content_type="image/png",
        monstore=monstore,
    )
    return facing


def _detect_reference_matte(raw: bytes) -> Color:
    """Sample the flat chroma-key border of a stored raw reference as its matte color."""
    with Image.open(io.BytesIO(raw)) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    border = np.concatenate(
        [rgb[0, :, :], rgb[-1, :, :], rgb[:, 0, :], rgb[:, -1, :]],
        axis=0,
    )
    red, green, blue = (int(channel) for channel in np.median(border, axis=0).astype(int))
    return Color(f"#{red:02X}{green:02X}{blue:02X}", "Detected matte", "Sampled from reference border")


def _read_likeness(path: pathlib.Path | None) -> tuple[bytes, str]:
    if path is None:
        raise SystemExit("--regenerate requires --likeness <path>.")
    suffix = path.suffix.lower().lstrip(".")
    media_type = _MEDIA_BY_SUFFIX.get(suffix)
    if media_type is None:
        raise SystemExit(f"--likeness must be PNG, JPEG, or WebP; got {path.suffix!r}.")
    return path.read_bytes(), media_type


if __name__ == "__main__":
    app()
