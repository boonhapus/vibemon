import io

from PIL import Image

from app.domains.sprite import types as sprite_types
from app.genai import sprite_facing


def test_resolve_gear_source_facing_uses_center_default() -> None:
    facing = sprite_facing.resolve_gear_source_facing(
        sprite_types.SpriteFacing.CENTER,
        "camera",
    )
    assert facing is sprite_types.SpriteFacing.LEFT


def test_derive_left_right_poses_from_right_source() -> None:
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    image.putpixel((12, 8), (200, 80, 40, 255))
    source = io.BytesIO()
    image.save(source, format="PNG")

    poses = sprite_facing.derive_left_right_poses(
        source.getvalue(),
        sprite_types.SpriteFacing.RIGHT,
    )

    right = Image.open(io.BytesIO(poses["right"]))
    left = Image.open(io.BytesIO(poses["left"]))
    right_pixel: tuple[int, int, int, int] = right.getpixel((12, 8))  # type: ignore[assignment]
    left_pixel: tuple[int, int, int, int] = left.getpixel((3, 8))  # type: ignore[assignment]
    assert right_pixel[3] > 0
    assert left_pixel[3] > 0
