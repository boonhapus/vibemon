"""Single seam for Lifecycle asset realization: generate → normalize → persist.

Public interface is the **Lifecycle** transitions (christen / manifest /
regenerate) plus the trainer-reference normalization the trainer pipeline needs.
The image pipeline (`sprite_postprocess`, `rmbg`, `pixelsnap`) is private to this
package — callers never touch numpy arrays, mattes, or grid dimensions.
"""

from PIL import Image

from app.domains.sprite import const as sprite_const
from app.domains.sprite import types as sprite_types
from app.domains.vibemon.brand import Color
from app.domains.vibemon.entity import Vibemon
from app.workflows import sprite_postprocess
from app.workflows.materialize_vibemon import AssetStore, MaterializeVibemon, VibemonAssetGenerator


async def christen_vibemon(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore: AssetStore | None = None,
    force: bool = False,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).christen(vibemon, force=force)


async def manifest_vibemon(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore: AssetStore | None = None,
    reference_bytes: bytes | None = None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).manifest(
        vibemon,
        reference_bytes=reference_bytes,
    )


async def regenerate_display_assets(
    vibemon: Vibemon,
    *,
    generator: VibemonAssetGenerator | None = None,
    monstore: AssetStore | None = None,
) -> Vibemon:
    return await MaterializeVibemon(generator=generator, monstore=monstore).regenerate_display_assets(vibemon)


def normalize_trainer_reference(image: bytes | Image.Image, *, bg_color: Color) -> bytes:
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
