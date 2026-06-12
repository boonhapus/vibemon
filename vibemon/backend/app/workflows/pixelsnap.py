"""Snap anti-aliased pixel-art renders onto a true low-res display grid."""

from PIL import Image

from app.domains.sprite import const as sprite_const


def snap(
    source: Image.Image,
    *,
    grid: int = sprite_const.REFERENCE_DISPLAY_GRID,
    quantize_palette: bool = False,
) -> Image.Image:
    """Downsample to a true pixel grid with hard alpha."""
    rgba = source.convert("RGBA")
    scale = max(rgba.width, rgba.height) / grid
    target = (max(1, round(rgba.width / scale)), max(1, round(rgba.height / scale)))

    small = rgba.resize(target, Image.Resampling.BOX)

    if quantize_palette:
        from app.workflows import _pixelsnap_palette

        small = _pixelsnap_palette.quantize_to_locked_palette(small)

    alpha = small.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    small.putalpha(alpha)
    return small


def snap_rgba_png(
    image: bytes | Image.Image,
    *,
    grid: int = sprite_const.REFERENCE_DISPLAY_GRID,
    quantize_palette: bool = False,
) -> bytes:
    """Return PNG bytes snapped to the display grid."""
    import io

    source = Image.open(io.BytesIO(image)) if isinstance(image, bytes) else image
    out = io.BytesIO()
    snap(source, grid=grid, quantize_palette=quantize_palette).save(out, format="PNG")
    return out.getvalue()
