import io

from PIL import Image

from app.domains.sprite import types as sprite_types
from app.workflows import asset_realization


def test_finalize_reference_display_orients_and_snaps() -> None:
    image = Image.new("RGBA", (256, 256), (200, 80, 40, 255))
    image.putpixel((220, 128), (255, 255, 255, 255))
    normalized = asset_realization.encode_rgba_png(image)

    display = Image.open(
        io.BytesIO(
            asset_realization.finalize_reference_display(
                normalized,
                facing=sprite_types.SpriteFacing.RIGHT,
            )
        )
    )

    assert max(display.size) == 128
    width = display.width
    assert display.getpixel((width // 4, display.height // 2))[3] == 255
    assert display.getpixel((width - width // 4, display.height // 2)) == (200, 80, 40, 255)
