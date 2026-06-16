"""Snap anti-aliased pixel-art renders onto a true low-res display grid."""

from PIL import Image
import numpy as np

from app.domains.sprite import const as sprite_const


def _min_pool_alpha(alpha: Image.Image, target: tuple[int, int]) -> Image.Image:
    """Downsample an alpha channel preserving transparency in mixed footprints."""
    target_w, target_h = target
    source = np.asarray(alpha, dtype=np.uint8)
    source_h, source_w = source.shape
    scale_x = source_w / target_w
    scale_y = source_h / target_h
    pooled = np.zeros((target_h, target_w), dtype=np.uint8)

    for row in range(target_h):
        y0 = int(row * scale_y)
        y1 = max(y0 + 1, int((row + 1) * scale_y))
        for col in range(target_w):
            x0 = int(col * scale_x)
            x1 = max(x0 + 1, int((col + 1) * scale_x))
            pooled[row, col] = int(source[y0:y1, x0:x1].min())
    return Image.fromarray(pooled, "L")


def snap(
    source: Image.Image,
    *,
    grid: int = sprite_const.REFERENCE_DISPLAY_GRID,
    quantize_palette: bool = False,
    adaptive_colors: int | None = None,
) -> Image.Image:
    """Downsample to a true pixel grid with hard alpha.

    The ``BOX`` resample leaves anti-aliased gradients across interior color
    boundaries, so generated sprites stay soft even after snapping. Passing
    ``adaptive_colors`` collapses those gradients onto a per-image palette of
    that size (median cut, no dither), which restores flat pixel-art regions
    without forcing off-palette hues. ``quantize_palette`` (the locked static
    palette) takes precedence when both are set.
    """
    rgba = source.convert("RGBA")
    scale = max(rgba.width, rgba.height) / grid
    target = (max(1, round(rgba.width / scale)), max(1, round(rgba.height / scale)))

    small = rgba.resize(target, Image.Resampling.BOX)
    small.putalpha(_min_pool_alpha(rgba.getchannel("A"), target))

    if quantize_palette:
        from app.workflows import _pixelsnap_palette

        small = _pixelsnap_palette.quantize_to_locked_palette(small)
    elif adaptive_colors is not None:
        small = _quantize_adaptive(small, adaptive_colors)

    alpha = small.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
    small.putalpha(alpha)
    return small


def _quantize_adaptive(image: Image.Image, colors: int) -> Image.Image:
    """Collapse to a per-image median-cut palette, preserving the alpha channel."""
    alpha = image.getchannel("A")
    quantized = (
        image.convert("RGB")
        .quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        .convert("RGBA")
    )
    quantized.putalpha(alpha)
    return quantized


def snap_rgba_png(
    image: bytes | Image.Image,
    *,
    grid: int = sprite_const.REFERENCE_DISPLAY_GRID,
    quantize_palette: bool = False,
    adaptive_colors: int | None = None,
) -> bytes:
    """Return PNG bytes snapped to the display grid."""
    import io

    source = Image.open(io.BytesIO(image)) if isinstance(image, bytes) else image
    out = io.BytesIO()
    snap(source, grid=grid, quantize_palette=quantize_palette, adaptive_colors=adaptive_colors).save(out, format="PNG")
    return out.getvalue()


def snap_profile_png(
    image: bytes | Image.Image,
    profile: sprite_const.SnapProfile,
) -> bytes:
    """Snap to the grid/palette of a display ``SnapProfile``.

    A profile with ``grid is None`` returns the source as RGBA PNG untouched, so
    contexts that must keep native resolution (e.g. the model-input reference)
    can share this entry point.
    """
    import io

    source = Image.open(io.BytesIO(image)) if isinstance(image, bytes) else image
    if profile.grid is None:
        out = io.BytesIO()
        source.convert("RGBA").save(out, format="PNG")
        return out.getvalue()
    return snap_rgba_png(source, grid=profile.grid, adaptive_colors=profile.colors)
