"""Single seam for Lifecycle asset realization: generate → normalize → persist."""

from PIL import Image

from app.domains.sprite import const as sprite_const
from app.domains.sprite import types as sprite_types
from app.domains.vibemon.brand import Color
from app.domains.vibemon.entity import Vibemon
from app.workflows import pixelsnap, sprite_postprocess
from app.workflows.materialize_vibemon import MaterializeVibemon, VibemonAssetGenerator


def normalize_trainer_reference(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Strip a generated trainer reference matte and return transparent RGBA PNG bytes."""
    return sprite_postprocess.normalize_trainer_reference_image(image, bg_color=bg_color)


def finalize_reference_display(
    normalized_rgba: bytes | Image.Image,
    *,
    facing: sprite_types.SpriteFacing,
    profile: sprite_const.SnapProfile = sprite_const.SHOWCASE_SNAP,
) -> bytes:
    """Orient a keyed reference to screen-left and snap to the display profile."""
    return sprite_postprocess.finalize_reference_display(normalized_rgba, facing=facing, profile=profile)


def normalize_matte_static_sprite(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Normalize a chroma-keyed static sprite and snap to the pixel grid."""
    rgba = normalize_trainer_reference(image, bg_color=bg_color)
    return pixelsnap.snap_rgba_png(rgba)


def normalize_vibemon_reference(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Key a generated Vibemon reference matte and return transparent RGBA PNG bytes."""
    return sprite_postprocess.normalize_reference_image(image, bg_color=bg_color)


def normalize_sprite_matte(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Key a sprite sheet and snap background pixels to a uniform matte RGB."""
    return sprite_postprocess.normalize_sprite_matte(image, bg_color=bg_color)


def validate_sprite_sheet(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
) -> list[str]:
    return sprite_postprocess.validate_sprite_sheet(image, bg_color=bg_color, rows=rows, cols=cols)


def extract_sprites(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
    padding: int = 8,
):
    return sprite_postprocess.extract_sprites(
        image,
        bg_color=bg_color,
        rows=rows,
        cols=cols,
        padding=padding,
    )


def encode_rgba_png(image: Image.Image) -> bytes:
    return sprite_postprocess.encode_rgba_png(image)


def compute_display_anchor(image: bytes | Image.Image):
    return sprite_postprocess.compute_display_anchor(image)


async def christen_vibemon(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore=None,
    force: bool = False,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).christen(vibemon, force=force)


async def christen_and_manifest_vibemon(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore=None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).christen_and_manifest(vibemon)


async def manifest_vibemon(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore=None,
    reference_bytes: bytes | None = None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).manifest(
        vibemon,
        reference_bytes=reference_bytes,
    )


async def reprocess_display_assets(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore=None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).reprocess_display_assets(vibemon)


async def regenerate_display_assets(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore=None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).regenerate_display_assets(vibemon)
