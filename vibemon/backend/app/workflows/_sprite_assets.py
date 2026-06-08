from collections.abc import Iterable
from typing import TYPE_CHECKING
import io

from PIL import Image
import numpy as np

from app.domains.vibemon.brand import Color
from app.domains.vibemon.types import PoseT

if TYPE_CHECKING:
    from app.domains.vibemon.entity import Vibemon

# Pixels at or above this alpha count as foreground for sheet validation and crops.
_FOREGROUND_ALPHA = 128
# When corner pixels are this far from the stored matte, trust corner sampling instead.
_MATTE_MISMATCH_DISTANCE = 45.0


def remove_solid_background(
    image: Image.Image,
    bg_color: tuple[int, int, int] | None = None,
    *,
    threshold_low: float = 45.0,
    threshold_high: float = 95.0,
    despill: bool = True,
) -> Image.Image:
    """Strip a solid-colored background via chroma keying.

    Converts pixel-to-background RGB distance into a soft alpha channel and
    optionally removes residual background tint from semi-transparent edges.
    Existing alpha on RGBA inputs is preserved so re-keying extracted crops
    does not turn transparent pixels into opaque black.
    """
    source = _to_pil(image)
    existing_alpha: np.ndarray | None = None
    if source.mode == "RGBA":
        rgba_arr = np.asarray(source, dtype=np.float32)
        existing_alpha = rgba_arr[..., 3] / 255.0
        rgb = rgba_arr[..., :3]
    else:
        rgb = np.asarray(source.convert("RGB"), dtype=np.float32)

    bg = _resolve_background_rgb(rgb, bg_color)

    distance = np.sqrt(((rgb - bg) ** 2).sum(-1))
    span = threshold_high - threshold_low
    if span > 0:
        keyed_alpha = np.clip((distance - threshold_low) / span, 0.0, 1.0)
    else:
        keyed_alpha = (distance > threshold_low).astype(np.float32)

    if existing_alpha is not None:
        alpha = np.clip(existing_alpha * keyed_alpha, 0.0, 1.0)
    else:
        alpha = keyed_alpha

    if despill:
        rgb = np.clip(rgb - bg * (1.0 - alpha)[..., None], 0.0, 255.0)

    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def resolve_background_color(
    image: Image.Image,
    bg_color: tuple[int, int, int] | None,
) -> tuple[int, int, int]:
    """Pick the chroma-key color for ``image``.

    Image models often ignore the requested matte and paint a different flat
    wash. When corner pixels are closer to each other than to the stored matte,
    sample the corners instead of forcing the stored value.
    """
    rgb = np.asarray(_to_pil(image).convert("RGB"), dtype=np.float32)
    detected = _sample_corner_background(rgb)
    if bg_color is None:
        return detected

    stored = np.array(bg_color, dtype=np.float32)
    corner_samples = _corner_pixels(rgb)
    stored_dist = float(np.sqrt(((corner_samples - stored) ** 2).sum(-1)).mean())
    detected_dist = float(np.sqrt(((corner_samples - detected) ** 2).sum(-1)).mean())
    if stored_dist > _MATTE_MISMATCH_DISTANCE and detected_dist + 1.0 < stored_dist:
        return detected
    return bg_color


def _resolve_background_rgb(
    rgb: np.ndarray,
    bg_color: tuple[int, int, int] | None,
) -> np.ndarray:
    resolved = resolve_background_color(Image.fromarray(rgb.astype(np.uint8), "RGB"), bg_color)
    return np.array(resolved, dtype=np.float32)


def _sample_corner_background(rgb: np.ndarray) -> tuple[int, int, int]:
    samples = _corner_pixels(rgb)
    mean = samples.mean(0)
    return int(mean[0]), int(mean[1]), int(mean[2])


def _corner_pixels(rgb: np.ndarray) -> np.ndarray:
    h, w = rgb.shape[:2]
    if h < 3 or w < 3:
        return rgb.reshape(-1, 3)
    offset = max(1, min(5, h // 20, w // 20))
    return np.stack(
        [
            rgb[offset, offset],
            rgb[offset, w - 1 - offset],
            rgb[h - 1 - offset, offset],
            rgb[h - 1 - offset, w - 1 - offset],
        ]
    )


def encode_rgba_png(image: Image.Image) -> bytes:
    """Persist a sprite with alpha for transparent UI rendering."""
    out = io.BytesIO()
    image.convert("RGBA").save(out, format="PNG")
    return out.getvalue()


def normalize_reference_image(image: bytes | Image.Image, vibemon: Vibemon) -> bytes:
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to normalize reference assets")
    source = _to_pil(image)
    matte = resolve_background_color(source, _hex_rgb(vibemon.aesthetic.background_color))
    rgba = remove_solid_background(source, bg_color=matte)
    return encode_rgba_png(rgba)


def normalize_pose_image(image: Image.Image, vibemon: Vibemon) -> bytes:
    """Strip matte from an extracted pose crop and save as transparent PNG."""
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to normalize pose assets")
    source = image.convert("RGBA")
    matte = _hex_rgb(vibemon.aesthetic.background_color)
    rgba = remove_solid_background(source, bg_color=matte)
    return encode_rgba_png(rgba)


def normalize_sheet_image(image: bytes | Image.Image, vibemon: Vibemon) -> bytes:
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to normalize sprite sheets")
    return normalize_sprite_matte(image, bg_color=vibemon.aesthetic.background_color)


def require_valid_sheet(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
) -> None:
    if issues := validate_sprite_sheet(image, bg_color=bg_color, rows=rows, cols=cols):
        raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")


def normalize_sprite_matte(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Flatten background noise to a uniform matte RGB PNG."""
    source = _to_pil(image)
    stored_matte = _hex_rgb(bg_color)
    effective_matte = resolve_background_color(source, stored_matte)
    rgba = remove_solid_background(source, bg_color=effective_matte)
    arr = np.asarray(rgba)
    rgb = arr[..., :3].copy()
    rgb[arr[..., 3] < _FOREGROUND_ALPHA] = stored_matte

    out = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(out, format="PNG")
    return out.getvalue()


def validate_sprite_sheet(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
) -> list[str]:
    source = _to_pil(image)
    matte = resolve_background_color(source, _hex_rgb(bg_color))
    rgba = remove_solid_background(source, bg_color=matte)
    fg = np.asarray(rgba)[..., 3] >= _FOREGROUND_ALPHA
    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    min_fg_per_cell = max(600, int(cell_area * 0.02))

    issues: list[str] = []
    for row, col, ys, xs in _cell_slices(fg.shape, rows=rows, cols=cols):
        cell_fg_count = int(fg[ys, xs].sum())
        if cell_fg_count < min_fg_per_cell:
            issues.append(f"R{row + 1}C{col + 1} has insufficient sprite content ({cell_fg_count} px)")

    return issues


def extract_sprites(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
    padding: int = 8,
) -> dict[PoseT, Image.Image]:
    source = _to_pil(image)
    matte = resolve_background_color(source, _hex_rgb(bg_color))
    rgba = remove_solid_background(source, bg_color=matte)
    arr = np.asarray(rgba)
    fg = arr[..., 3] >= _FOREGROUND_ALPHA

    if not fg.any():
        raise RuntimeError("No foreground detected. Is the matte color clearly distinct from the sprites?")

    aligned: list[Image.Image] = []
    for _, _, ys_cell, xs_cell in _cell_slices(fg.shape, rows=rows, cols=cols):
        cell_fg = fg[ys_cell, xs_cell]
        if not cell_fg.any():
            aligned.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            continue

        ys2, xs2 = np.where(cell_fg)
        cell_h, cell_w = cell_fg.shape
        y0 = max(0, int(ys2.min()) - padding)
        x0 = max(0, int(xs2.min()) - padding)
        y1 = min(cell_h, int(ys2.max()) + 1 + padding)
        x1 = min(cell_w, int(xs2.max()) + 1 + padding)

        crop = arr[ys_cell, xs_cell][y0:y1, x0:x1]
        aligned.append(Image.fromarray(crop, "RGBA"))

    if len(aligned) != rows * cols:
        raise RuntimeError(f"expected {rows * cols} extracted sprites, got {len(aligned)}")

    return dict(zip(PoseT, aligned, strict=True))


def _hex_rgb(color: object) -> tuple[int, int, int]:
    value = str(color).strip()
    if not value.startswith("#") or len(value) != 7:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")

    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _to_pil(image: bytes | Image.Image) -> Image.Image:
    return image if isinstance(image, Image.Image) else Image.open(io.BytesIO(image))


def _cell_slices(shape: tuple[int, int], *, rows: int, cols: int) -> Iterable[tuple[int, int, slice, slice]]:
    h, w = shape[:2]

    for row in range(rows):
        y0 = int(row * h / rows)
        y1 = h if row == rows - 1 else int((row + 1) * h / rows)
        for col in range(cols):
            x0 = int(col * w / cols)
            x1 = w if col == cols - 1 else int((col + 1) * w / cols)
            yield row, col, slice(y0, y1), slice(x0, x1)
