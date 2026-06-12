"""Canonical left-facing orientation for standing reference sprites."""

import io

from PIL import Image, ImageOps

from app.domains.sprite import types as sprite_types


def should_mirror_to_face_left(facing: sprite_types.SpriteFacing) -> bool:
    """Return whether a reference sprite should be mirrored to face screen-left."""
    return facing is not sprite_types.SpriteFacing.LEFT


def orient_reference_left(
    image: bytes | Image.Image,
    *,
    facing: sprite_types.SpriteFacing,
) -> bytes:
    """Mirror a reference sprite when it is not already facing screen-left."""
    source = Image.open(io.BytesIO(image)).convert("RGBA") if isinstance(image, bytes) else image.convert("RGBA")

    if not should_mirror_to_face_left(facing):
        return _encode_rgba_png(source)

    return _encode_rgba_png(ImageOps.mirror(source))


def _encode_rgba_png(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.convert("RGBA").save(out, format="PNG")
    return out.getvalue()
