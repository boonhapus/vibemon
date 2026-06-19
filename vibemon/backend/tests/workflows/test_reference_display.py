import io

from PIL import Image

from app.domains.sprite import types as sprite_types
from app.workflows import pixelsnap, sprite_postprocess


def test_finalize_reference_display_orients_and_snaps() -> None:
    image = Image.new("RGBA", (768, 768), (200, 80, 40, 255))
    image.paste((255, 255, 255, 255), (600, 360, 660, 420))
    normalized = sprite_postprocess.encode_rgba_png(image)

    display = Image.open(
        io.BytesIO(
            sprite_postprocess.finalize_reference_display(
                normalized,
                facing=sprite_types.SpriteFacing.RIGHT,
            )
        )
    )

    # Showcase profile: large on screen, lightly snapped to a 384px long edge.
    assert max(display.size) == 384
    width = display.width
    display_pixel: tuple[int, int, int, int] = display.getpixel((width // 4, display.height // 2))  # type: ignore[assignment]
    assert display_pixel[3] == 255
    assert display.getpixel((width - width // 4, display.height // 2)) == (200, 80, 40, 255)


def test_snap_preserves_transparent_gaps_on_downsample() -> None:
    image = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    for y in range(8, 24):
        image.putpixel((10, y), (80, 140, 60, 255))
        image.putpixel((21, y), (80, 140, 60, 255))

    snapped = pixelsnap.snap(image, grid=16, adaptive_colors=8)

    snapped_pixel: tuple[int, int, int, int] = snapped.getpixel((8, 8))  # type: ignore[assignment]
    assert snapped_pixel[3] == 0


def test_adaptive_quantize_collapses_gradient_to_flat_regions() -> None:
    gradient = Image.new("RGBA", (256, 256))
    for x in range(256):
        for y in range(256):
            gradient.putpixel((x, y), (x, y, 128, 255))

    box_only = pixelsnap.snap(gradient, grid=128)
    adaptive = pixelsnap.snap(gradient, grid=128, adaptive_colors=16)

    adaptive_colors = adaptive.getcolors(maxcolors=1 << 16)
    assert adaptive_colors is not None
    opaque = [rgba[:3] for _, rgba in adaptive_colors if rgba[3] == 255]  # pyrefly: ignore
    assert len(set(opaque)) <= 16
    box_only_colors = box_only.getcolors(maxcolors=1 << 16)
    assert box_only_colors is not None
    assert len(box_only_colors) > 16
