"""Trainer reference pipeline: likeness photo → styled, normalized, persisted sprite."""

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets
from app.genai import vibemon_assets
from app.storage.blob import assets as blob_assets
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import models
from app.workflows import asset_realization

_LOGGER = structlog.get_logger(__name__)


async def upload_trainer_reference(
    sess: AsyncSession,
    trainer: models.Trainer,
    *,
    likeness: bytes,
    media_type: str,
) -> sprite_types.SpriteFacing:
    """Generate, normalize, and persist a trainer reference sprite from a likeness photo.

    Raises ValueError when the likeness is unusable or generation is refused.
    """
    vibemon_assets.validate_reference_likeness(likeness, media_type=media_type)

    generator = vibemon_assets.get_default_asset_generator()
    raw_reference, background_color = await generator.generate_trainer_reference(
        likeness,
        username=trainer.username,
        likeness_media_type=media_type,
    )

    normalized_reference = asset_realization.normalize_trainer_reference(
        raw_reference,
        bg_color=background_color,
    )

    try:
        reference_facing = await generator.detect_trainer_reference_facing(normalized_reference)
    except Exception as exc:
        await _LOGGER.awarn("trainer_reference_facing_detection_failed", error=str(exc))
        reference_facing = sprite_types.SpriteFacing.RIGHT

    display_reference = asset_realization.finalize_reference_display(
        normalized_reference,
        facing=reference_facing,
    )
    trainer.reference_detected_facing = reference_facing.value
    monstore = get_default_monstore()
    await blob_assets.append_trainer_asset(
        sess,
        trainer.id,
        trainer_assets.TrainerAssetKind.REFERENCE_RAW,
        raw_reference,
        content_type="image/png",
        monstore=monstore,
    )
    await blob_assets.append_trainer_asset(
        sess,
        trainer.id,
        trainer_assets.TrainerAssetKind.REFERENCE,
        display_reference,
        content_type="image/png",
        monstore=monstore,
    )
    await _LOGGER.ainfo(
        "trainer_reference_stored",
        trainer_id=str(trainer.id),
        size_bytes=len(display_reference),
        reference_detected_facing=reference_facing.value,
    )
    return reference_facing
