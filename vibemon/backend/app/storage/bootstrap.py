"""Seed canonical catalog rows and monstore blobs after schema init."""

import hashlib
import pathlib

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa
import structlog

from app.core import asset_paths
from app.core.time import resolve_clock
from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets
from app.domains.trainer import const as trainer_const
from app.storage.blob.monstore import MonStore, get_default_monstore
from app.storage.database import models

_LOGGER = structlog.get_logger(__name__)
_CANONICAL_REFERENCE_REVISION = 1


def canonical_trainer_raw_path() -> pathlib.Path:
    """Return the shipped style-bible ``trainer.png`` under the frontend static tree."""
    return asset_paths.CANONICAL_TRAINER_REFERENCE


def canonical_trainer_display_path() -> pathlib.Path:
    """Return the pixelsnapped ``trainer@128.png`` used for UI display."""
    return asset_paths.CANONICAL_TRAINER_DISPLAY


def load_canonical_trainer_raw_png() -> bytes:
    """Read bytes for the default trainer GenAI/style-bible source."""
    return asset_paths.load_canonical_trainer_raw_png()


def load_canonical_trainer_display_png() -> bytes:
    """Read bytes for the default trainer snapped display sprite."""
    return asset_paths.load_canonical_trainer_display_png()


async def seed_canonical_trainer(
    sess: AsyncSession,
    *,
    monstore: MonStore | None = None,
) -> bool:
    """Ensure the reserved style-bible trainer row and reference revisions exist.

    Returns ``True`` when a new blob or database row was written, ``False`` when
    the canonical reference was already present with matching content.
    """
    asset_store = monstore or get_default_monstore()
    raw_bytes = load_canonical_trainer_raw_png()
    display_bytes = load_canonical_trainer_display_png()
    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    display_sha256 = hashlib.sha256(display_bytes).hexdigest()
    raw_key = asset_store.trainer_asset_key(
        trainer_const.CANONICAL_TRAINER_ID,
        trainer_assets.TrainerAssetKind.REFERENCE_RAW,
        _CANONICAL_REFERENCE_REVISION,
    )
    display_key = asset_store.trainer_asset_key(
        trainer_const.CANONICAL_TRAINER_ID,
        trainer_assets.TrainerAssetKind.REFERENCE,
        _CANONICAL_REFERENCE_REVISION,
    )

    trainer = await sess.get(models.Trainer, trainer_const.CANONICAL_TRAINER_ID)
    if trainer is None:
        sess.add(
            models.Trainer(
                id=trainer_const.CANONICAL_TRAINER_ID,
                username=trainer_const.CANONICAL_TRAINER_USERNAME,
                reference_detected_facing=sprite_types.SpriteFacing.LEFT.value,
            )
        )
        await sess.flush()
    elif trainer.reference_detected_facing is None:
        trainer.reference_detected_facing = sprite_types.SpriteFacing.LEFT.value

    existing_rows = (
        (
            await sess.execute(
                sa.select(models.TrainerAsset).where(
                    models.TrainerAsset.trainer_id == trainer_const.CANONICAL_TRAINER_ID,
                    models.TrainerAsset.kind.in_(
                        (
                            trainer_assets.TrainerAssetKind.REFERENCE_RAW.value,
                            trainer_assets.TrainerAssetKind.REFERENCE.value,
                        )
                    ),
                )
            )
        )
        .scalars()
        .all()
    )
    rows_by_kind = {row.kind: row for row in existing_rows}

    raw_row = rows_by_kind.get(trainer_assets.TrainerAssetKind.REFERENCE_RAW.value)
    display_row = rows_by_kind.get(trainer_assets.TrainerAssetKind.REFERENCE.value)
    if (
        raw_row is not None
        and display_row is not None
        and raw_row.sha256 == raw_sha256
        and display_row.sha256 == display_sha256
        and raw_row.object_key == raw_key
        and display_row.object_key == display_key
        and await asset_store.has(raw_key)
        and await asset_store.has(display_key)
    ):
        return False

    await asset_store.put_bytes(raw_key, raw_bytes)
    await asset_store.put_bytes(display_key, display_bytes)
    now = resolve_clock()

    if raw_row is None:
        sess.add(
            models.TrainerAsset(
                trainer_id=trainer_const.CANONICAL_TRAINER_ID,
                kind=trainer_assets.TrainerAssetKind.REFERENCE_RAW.value,
                selected_revision=_CANONICAL_REFERENCE_REVISION,
                max_revision=_CANONICAL_REFERENCE_REVISION,
                object_key=raw_key,
                content_type="image/png",
                byte_size=len(raw_bytes),
                sha256=raw_sha256,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        raw_row.selected_revision = _CANONICAL_REFERENCE_REVISION
        raw_row.max_revision = _CANONICAL_REFERENCE_REVISION
        raw_row.object_key = raw_key
        raw_row.content_type = "image/png"
        raw_row.byte_size = len(raw_bytes)
        raw_row.sha256 = raw_sha256
        raw_row.updated_at = now

    if display_row is None:
        sess.add(
            models.TrainerAsset(
                trainer_id=trainer_const.CANONICAL_TRAINER_ID,
                kind=trainer_assets.TrainerAssetKind.REFERENCE.value,
                selected_revision=_CANONICAL_REFERENCE_REVISION,
                max_revision=_CANONICAL_REFERENCE_REVISION,
                object_key=display_key,
                content_type="image/png",
                byte_size=len(display_bytes),
                sha256=display_sha256,
                created_at=now,
                updated_at=now,
            )
        )
    else:
        display_row.selected_revision = _CANONICAL_REFERENCE_REVISION
        display_row.max_revision = _CANONICAL_REFERENCE_REVISION
        display_row.object_key = display_key
        display_row.content_type = "image/png"
        display_row.byte_size = len(display_bytes)
        display_row.sha256 = display_sha256
        display_row.updated_at = now

    await _LOGGER.ainfo(
        "seeded_canonical_trainer_reference",
        trainer_id=str(trainer_const.CANONICAL_TRAINER_ID),
        raw_object_key=raw_key,
        display_object_key=display_key,
        raw_byte_size=len(raw_bytes),
        display_byte_size=len(display_bytes),
    )
    return True


async def seed_defaults(
    sess: AsyncSession,
    *,
    monstore: MonStore | None = None,
) -> bool:
    """Seed all catalog defaults required for a fresh environment."""
    return await seed_canonical_trainer(sess, monstore=monstore)
