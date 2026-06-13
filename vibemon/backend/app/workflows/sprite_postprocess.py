from collections.abc import Iterable
import io

from PIL import Image
import numpy as np

from app.domains.sprite import const as sprite_const
from app.domains.sprite import orient as sprite_orient
from app.domains.sprite import types as sprite_types
from app.domains.vibemon.assets import SpriteAnchor
from app.domains.vibemon.brand import Color
from app.domains.vibemon.types import PoseT
from app.workflows import pixelsnap, rmbg


def encode_rgba_png(image: Image.Image) -> bytes:
    """Persist a sprite with alpha for transparent UI rendering."""
    out = io.BytesIO()
    image.convert("RGBA").save(out, format="PNG")
    return out.getvalue()


def normalize_trainer_reference_image(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Strip the generated trainer reference matte."""
    source = rmbg.to_pil(image)
    stored_matte = bg_color.as_rgb()
    snapped = rmbg.snap_painted_matte(source, stored_matte=stored_matte)
    rgba = rmbg.key_sprite(snapped, bg_color=stored_matte)
    rgba = rmbg.punch_enclosed_matte_holes(rgba, stored_matte=stored_matte)
    return encode_rgba_png(rgba)


def normalize_reference_image(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Key a generated reference matte and return a transparent RGBA PNG."""
    source = rmbg.to_pil(image)
    stored_matte = bg_color.as_rgb()
    rgb_source = _prepare_reference_source(source, stored_matte)
    rgba = rmbg.key_sprite(rgb_source, bg_color=stored_matte)
    return encode_rgba_png(rgba)


def finalize_reference_display(
    normalized_rgba: bytes | Image.Image,
    *,
    facing: sprite_types.SpriteFacing,
    profile: sprite_const.SnapProfile = sprite_const.SHOWCASE_SNAP,
) -> bytes:
    """Orient a keyed reference to screen-left, then snap to the display profile.

    Defaults to the showcase profile: the reference shown on screen is large, so
    it is only lightly snapped. The model-input reference is the unsnapped
    ``REFERENCE_RAW`` blob and is never routed through here.
    """
    oriented = sprite_orient.orient_reference_left(normalized_rgba, facing=facing)
    return pixelsnap.snap_profile_png(oriented, profile)


def snap_pose_display(
    image: bytes | Image.Image,
    *,
    profile: sprite_const.SnapProfile,
) -> bytes:
    """Snap an extracted pose sprite to its display profile (battle vs emote)."""
    return pixelsnap.snap_profile_png(image, profile)


def compute_display_anchor(image: bytes | Image.Image) -> SpriteAnchor | None:
    """Alpha-scan a display sprite for its content bbox and feet anchor (canvas fractions)."""
    rgba = rmbg.to_pil(image).convert("RGBA")
    opaque = np.asarray(rgba)[..., 3] >= 128
    if not opaque.any():
        return None

    ys, xs = np.where(opaque)
    h, w = opaque.shape
    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())

    # Feet midpoint: x midrange of opaque pixels in the bottom slice of the content box.
    feet_rows = max(2, round((bottom - top + 1) * 0.06))
    _, feet_xs = np.where(opaque[bottom - feet_rows + 1 : bottom + 1, :])
    anchor_x = (int(feet_xs.min()) + int(feet_xs.max()) + 1) / 2 / w

    return SpriteAnchor(
        anchor_x=anchor_x,
        baseline_y=(bottom + 1) / h,
        content_box=(left / w, top / h, (right + 1) / w, (bottom + 1) / h),
    )


def normalize_sprite_matte(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
) -> bytes:
    """Key a sprite sheet and snap background pixels to a uniform matte RGB."""
    source = rmbg.to_pil(image)
    stored_matte = bg_color.as_rgb()
    rgba = rmbg.key_sprite(
        source,
        bg_color=stored_matte,
        despill=True,
        keep_specks=True,
    )
    arr = np.asarray(rgba)
    rgb = arr[..., :3].copy()
    rgb[arr[..., 3] < 128] = stored_matte

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
    source = rmbg.to_pil(image).convert("RGB")
    matte = bg_color.as_rgb()
    fg = _sheet_foreground_mask(np.asarray(source), matte)
    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    min_fg_per_cell = max(600, int(cell_area * 0.02))

    issues: list[str] = []
    for row, col, ys, xs in _cell_slices(fg.shape, rows=rows, cols=cols):
        cell_fg_count = int(fg[ys, xs].sum())
        if cell_fg_count < min_fg_per_cell:
            issues.append(f"R{row + 1}C{col + 1} has insufficient sprite content ({cell_fg_count} px)")

    return issues


def extract_grid_cells(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int,
    cols: int,
    padding: int = 8,
) -> list[Image.Image]:
    """Extract row-major RGBA crops from a keyed RGB contact sheet."""
    source = rmbg.to_pil(image).convert("RGB")
    matte = bg_color.as_rgb()
    rgb = np.asarray(source)
    fg = _sheet_foreground_mask(rgb, matte)

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

        crop_rgb = rgb[ys_cell, xs_cell][y0:y1, x0:x1]
        crop_fg = cell_fg[y0:y1, x0:x1]
        alpha = np.where(crop_fg, 255, 0).astype(np.uint8)
        crop = np.dstack([crop_rgb, alpha])
        aligned.append(Image.fromarray(crop, "RGBA"))

    expected = rows * cols
    if len(aligned) != expected:
        raise RuntimeError(f"expected {expected} extracted sprites, got {len(aligned)}")

    return aligned


def extract_sprites(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
    padding: int = 8,
) -> dict[PoseT, Image.Image]:
    aligned = extract_grid_cells(
        image,
        bg_color=bg_color,
        rows=rows,
        cols=cols,
        padding=padding,
    )
    return dict(zip(PoseT, aligned, strict=True))


def _sheet_foreground_mask(rgb: np.ndarray, matte: tuple[int, int, int]) -> np.ndarray:
    matte_rgb = np.array(matte, dtype=rgb.dtype)
    return np.any(rgb[..., :3] != matte_rgb, axis=-1)


def _prepare_reference_source(
    image: Image.Image,
    matte: tuple[int, int, int],
) -> Image.Image:
    """Return RGB suitable for a fresh reference key pass."""
    if image.mode == "RGBA":
        alpha = np.asarray(image)[..., 3]
        if (alpha < 250).any():
            return _flatten_rgba_on_matte(image, matte)
    return image.convert("RGB")


def _flatten_rgba_on_matte(
    image: Image.Image,
    matte: tuple[int, int, int],
) -> Image.Image:
    rgba = image.convert("RGBA")
    background = Image.new("RGBA", rgba.size, (*matte, 255))
    return Image.alpha_composite(background, rgba).convert("RGB")


def _cell_slices(shape: tuple[int, int], *, rows: int, cols: int) -> Iterable[tuple[int, int, slice, slice]]:
    h, w = shape[:2]

    for row in range(rows):
        y0 = int(row * h / rows)
        y1 = h if row == rows - 1 else int((row + 1) * h / rows)
        for col in range(cols):
            x0 = int(col * w / cols)
            x1 = w if col == cols - 1 else int((col + 1) * w / cols)
            yield row, col, slice(y0, y1), slice(x0, x1)
