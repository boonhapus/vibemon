from collections.abc import Iterable
import io

from PIL import Image
from scipy import ndimage
import numpy as np

from app.domains.vibemon.brand import Color
from app.domains.vibemon.types import PoseT


def _hue_distance(hue: np.ndarray, center: float) -> np.ndarray:
    return np.abs((hue - center + 0.5) % 1.0 - 0.5)


def _edge_pixels(arr: np.ndarray, *, border: int = 6) -> np.ndarray:
    h, w = arr.shape[:2]
    border = max(1, min(border, max(1, h // 2), max(1, w // 2)))
    c = arr.shape[2]

    return np.concatenate(
        [
            arr[:border, :].reshape(-1, c),
            arr[-border:, :].reshape(-1, c),
            arr[:, :border].reshape(-1, c),
            arr[:, -border:].reshape(-1, c),
        ]
    )


def _dominant_background_sample_mask(
    arr: np.ndarray,
    lab: np.ndarray,
    edge_center: np.ndarray,
    edge_dist: np.ndarray,
) -> np.ndarray:
    flat_rgb = arr.reshape(-1, 3)
    quantized = (flat_rgb // 16).astype(np.uint16)
    bin_ids = quantized[:, 0] * 256 + quantized[:, 1] * 16 + quantized[:, 2]
    unique_ids, counts = np.unique(bin_ids, return_counts=True)
    top_ids = unique_ids[np.argsort(counts)[-16:]]

    top_color_mask = np.isin(bin_ids, top_ids).reshape(arr.shape[:2])
    distance_to_edge_center = np.linalg.norm(lab - edge_center, axis=2)
    dominant_tolerance = max(float(np.percentile(edge_dist, 99.5)) * 4 + 8, 24.0)

    return top_color_mask & (distance_to_edge_center <= dominant_tolerance)


def _background_lab_distances(arr: np.ndarray, *, border: int = 6) -> tuple[np.ndarray, float, float]:
    from skimage.color import rgb2lab

    STRICT_PCT, STRICT_SCALE, STRICT_OFFSET = 99.5, 1.3, 2.0
    STRICT_LO, STRICT_HI = 6.0, 16.0
    CAND_PCT, CAND_SCALE, CAND_OFFSET = 99.7, 1.8, 5.0
    CAND_LO_FLOOR, CAND_HI = 18.0, 42.0
    CAND_STRICT_MARGIN = 8.0
    RUNAWAY_FRACTION = 0.84

    lab = rgb2lab(arr / 255.0)
    edge_lab = _edge_pixels(lab, border=border)
    edge_center = np.median(edge_lab, axis=0)
    edge_dist = np.linalg.norm(edge_lab - edge_center, axis=1)

    strict_tolerance = float(
        np.clip(
            np.percentile(edge_dist, STRICT_PCT) * STRICT_SCALE + STRICT_OFFSET,
            STRICT_LO,
            STRICT_HI,
        )
    )
    cand_lo = max(CAND_LO_FLOOR, strict_tolerance + CAND_STRICT_MARGIN)
    edge_candidate_tolerance = float(
        np.clip(
            np.percentile(edge_dist, CAND_PCT) * CAND_SCALE + CAND_OFFSET,
            cand_lo,
            CAND_HI,
        )
    )

    dominant_bg = _dominant_background_sample_mask(arr, lab, edge_center, edge_dist)
    sample_lab = np.concatenate([edge_lab, lab[dominant_bg]]) if dominant_bg.any() else edge_lab
    center = np.median(sample_lab, axis=0)

    dist = np.linalg.norm(lab - center, axis=2)
    sample_dist = np.linalg.norm(sample_lab - center, axis=1)
    candidate_tolerance = float(
        np.clip(
            np.percentile(sample_dist, CAND_PCT) * CAND_SCALE + CAND_OFFSET,
            cand_lo,
            CAND_HI,
        )
    )

    if (dist <= candidate_tolerance).mean() > RUNAWAY_FRACTION:
        dist = np.linalg.norm(lab - edge_center, axis=2)
        candidate_tolerance = edge_candidate_tolerance

    return dist, strict_tolerance, candidate_tolerance


def _same_hue_shadow_mask(arr: np.ndarray, *, border: int = 6) -> np.ndarray:
    from skimage.color import rgb2hsv

    hsv = rgb2hsv(arr / 255.0)
    edge_hsv = _edge_pixels(hsv, border=border)

    if float(np.median(edge_hsv[:, 1])) < 0.05:
        return np.zeros(arr.shape[:2], dtype=bool)

    angles = edge_hsv[:, 0] * 2 * np.pi
    hue_center = (np.arctan2(np.sin(angles).mean(), np.cos(angles).mean()) / (2 * np.pi)) % 1.0
    edge_hue_dist = _hue_distance(edge_hsv[:, 0], float(hue_center))
    hue_tolerance = min(max(float(np.percentile(edge_hue_dist, 99.5)) * 2 + 0.015, 0.035), 0.08)

    s_lo, s_hi = np.percentile(edge_hsv[:, 1], [0.5, 99.5])
    v_hi = float(np.percentile(edge_hsv[:, 2], 99.5))

    return (
        (_hue_distance(hsv[..., 0], float(hue_center)) <= hue_tolerance)
        & (hsv[..., 1] >= max(float(s_lo) - 0.20, 0.0))
        & (hsv[..., 1] <= min(float(s_hi) + 0.20, 1.0))
        & (hsv[..., 2] <= min(v_hi + 0.08, 1.0))
    )


def _background_masks_from_edges(arr: np.ndarray, *, border: int = 6) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lab_dist, strict_tolerance, candidate_tolerance = _background_lab_distances(arr, border=border)
    strict_bg = lab_dist <= strict_tolerance
    lab_candidate_bg = lab_dist <= candidate_tolerance
    candidate_bg = lab_candidate_bg | _same_hue_shadow_mask(arr, border=border)

    return strict_bg, candidate_bg, lab_candidate_bg


def _border_seed(mask: np.ndarray) -> np.ndarray:
    seed = np.zeros_like(mask, dtype=bool)
    seed[0, :] = mask[0, :]
    seed[-1, :] = mask[-1, :]
    seed[:, 0] = mask[:, 0]
    seed[:, -1] = mask[:, -1]

    return seed


def _connected_from_seeds(mask: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    labels, count = ndimage.label(mask)

    if count == 0:
        return np.zeros_like(mask, dtype=bool)

    seed_labels = np.unique(labels[seeds & mask])
    seed_labels = seed_labels[seed_labels != 0]

    if len(seed_labels) == 0:
        return np.zeros_like(mask, dtype=bool)

    return np.isin(labels, seed_labels)


def _connected_to_edges(mask: np.ndarray) -> np.ndarray:
    return _connected_from_seeds(mask, _border_seed(mask))


def _cell_slices(shape: tuple[int, int], *, rows: int, cols: int) -> Iterable[tuple[int, int, slice, slice]]:
    h, w = shape[:2]

    for row in range(rows):
        y0 = int(row * h / rows)
        y1 = h if row == rows - 1 else int((row + 1) * h / rows)
        for col in range(cols):
            x0 = int(col * w / cols)
            x1 = w if col == cols - 1 else int((col + 1) * w / cols)
            yield row, col, slice(y0, y1), slice(x0, x1)


def _cell_edge_connected_background(bg_candidate: np.ndarray, *, rows: int, cols: int) -> np.ndarray:
    local_bg = np.zeros_like(bg_candidate, dtype=bool)

    for _, _, ys, xs in _cell_slices(bg_candidate.shape, rows=rows, cols=cols):
        local_bg[ys, xs] |= _connected_to_edges(bg_candidate[ys, xs])

    return local_bg


def _remove_large_background_holes(
    fg: np.ndarray,
    bg_candidate: np.ndarray,
    *,
    rows: int,
    cols: int,
) -> np.ndarray:
    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    cell_span = max(h / rows, w / cols)
    max_keep_area = min(max(cell_area * 0.0018, 80.0), 360.0)
    max_keep_span = min(max(cell_span * 0.07, 12.0), 42.0)

    hole_like = fg & bg_candidate
    labels, count = ndimage.label(hole_like)

    if count == 0:
        return fg

    sizes = np.bincount(labels.ravel())
    objects = ndimage.find_objects(labels)
    remove_ids: list[int] = []

    for label_id, obj in enumerate(objects, start=1):
        if obj is None:
            continue

        ys, xs = obj
        area = int(sizes[label_id])
        height = ys.stop - ys.start
        width = xs.stop - xs.start

        if area > max_keep_area or max(height, width) > max_keep_span:
            remove_ids.append(label_id)

    if not remove_ids:
        return fg

    return fg & ~np.isin(labels, remove_ids)


def _largest_component(mask: np.ndarray) -> tuple[np.ndarray, int]:
    labels, count = ndimage.label(mask)

    if count == 0:
        return np.zeros_like(mask, dtype=bool), 0

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    keep = int(sizes.argmax())

    return labels == keep, int(sizes[keep])


def _remove_small_components(mask: np.ndarray, *, min_area: int) -> np.ndarray:
    labels, count = ndimage.label(mask)

    if count == 0:
        return mask

    sizes = np.bincount(labels.ravel())
    keep = sizes >= min_area
    keep[0] = False
    filtered = keep[labels]

    return filtered if filtered.any() else mask


def _bounds_mask_without_soft_highlights(arr: np.ndarray, fg: np.ndarray) -> np.ndarray:
    from skimage.color import rgb2hsv

    hsv = rgb2hsv(arr / 255.0)
    soft_highlight = (hsv[..., 1] <= 0.22) & (hsv[..., 2] >= 0.62)
    solid_support = fg & ~soft_highlight

    if not solid_support.any():
        return fg

    supported_highlight = ndimage.binary_dilation(solid_support, iterations=3) & soft_highlight
    bounds_mask = fg & (~soft_highlight | supported_highlight)

    return bounds_mask if bounds_mask.any() else fg


def _fill_transparent_rgb(rgb: np.ndarray, alpha_mask: np.ndarray) -> np.ndarray:
    filled = rgb.copy()
    transparent = ~alpha_mask

    if not transparent.any() or not alpha_mask.any():
        return filled

    indices = ndimage.distance_transform_edt(
        transparent,
        return_distances=False,
        return_indices=True,
    )
    if indices is None:
        return filled

    filled[transparent] = rgb[tuple(axis[transparent] for axis in indices)]

    return filled


def _foreground_mask_from_generated_matte(
    arr: np.ndarray,
    *,
    rows: int,
    cols: int,
) -> tuple[np.ndarray, np.ndarray]:
    strict_bg, bg_candidate, _ = _background_masks_from_edges(arr)
    sheet_bg = _connected_from_seeds(bg_candidate, _border_seed(strict_bg))
    cell_bg = _cell_edge_connected_background(bg_candidate, rows=rows, cols=cols)
    fg = ~(sheet_bg | cell_bg)
    fg = _remove_large_background_holes(fg, strict_bg, rows=rows, cols=cols)

    return fg, bg_candidate


def _hex_rgb(color: object) -> tuple[int, int, int]:
    value = str(color).strip()
    if not value.startswith("#") or len(value) != 7:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")

    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _to_pil(image: bytes | Image.Image) -> Image.Image:
    return image if isinstance(image, Image.Image) else Image.open(io.BytesIO(image))


def _image_to_rgb_array(image: bytes | Image.Image) -> np.ndarray:
    return np.array(_to_pil(image).convert("RGB"))


def _simple_foreground(arr: np.ndarray, *, threshold: float = 30.0) -> np.ndarray:
    bg = np.median(_edge_pixels(arr, border=6), axis=0)

    return np.linalg.norm(arr.astype(np.float32) - bg, axis=2) > threshold


def _normalize_fg_strict(arr: np.ndarray, *, rows: int, cols: int) -> np.ndarray:
    fg, _ = _foreground_mask_from_generated_matte(arr, rows=rows, cols=cols)

    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    min_keep_area = max(24, int(cell_area * 0.0005))
    clean_fg = np.zeros_like(fg, dtype=bool)

    for _, _, ys, xs in _cell_slices(fg.shape, rows=rows, cols=cols):
        largest, size = _largest_component(fg[ys, xs])
        if size >= min_keep_area:
            clean_fg[ys, xs] |= largest

    return ndimage.binary_fill_holes(clean_fg)


def normalize_sprite_matte(
    image: bytes | Image.Image,
    *,
    bg_color: Color,
    rows: int = 3,
    cols: int = 3,
    strict_matte: bool = False,
) -> bytes:
    arr = _image_to_rgb_array(image)
    clean_fg = _normalize_fg_strict(arr, rows=rows, cols=cols) if strict_matte else _simple_foreground(arr)
    normalized = arr.copy()
    normalized[~clean_fg] = _hex_rgb(bg_color)

    out = io.BytesIO()
    Image.fromarray(normalized, "RGB").save(out, format="PNG")
    return out.getvalue()


def _validate_strict(arr: np.ndarray, *, rows: int, cols: int) -> list[str]:
    h, w = arr.shape[:2]
    cell_area = (h / rows) * (w / cols)
    min_main_area = max(600, int(cell_area * 0.02))
    fg, _ = _foreground_mask_from_generated_matte(arr, rows=rows, cols=cols)

    labels, count = ndimage.label(fg)
    sizes = np.bincount(labels.ravel()) if count else np.array([0])
    major_labels = [label_id for label_id in range(1, count + 1) if sizes[label_id] >= min_main_area]

    issues: list[str] = []
    expected = rows * cols

    if len(major_labels) != expected:
        issues.append(f"expected {expected} main sprite bodies, found {len(major_labels)}")

    cell_counts = np.zeros((rows, cols), dtype=np.int16)
    for label_id in major_labels:
        ys, xs = np.where(labels == label_id)
        cy = int(float(ys.mean()))
        cx = int(float(xs.mean()))
        row = min(rows - 1, int(cy * rows / h))
        col = min(cols - 1, int(cx * cols / w))
        cell_counts[row, col] += 1

    for row in range(rows):
        for col in range(cols):
            count_in_cell = int(cell_counts[row, col])
            cell_name = f"R{row + 1}C{col + 1}"

            if count_in_cell == 0:
                issues.append(f"{cell_name} has no main sprite body")
            elif count_in_cell > 1:
                issues.append(f"{cell_name} contains {count_in_cell} main sprite bodies")

    return issues


def _validate_simple(arr: np.ndarray, *, rows: int, cols: int) -> list[str]:
    fg = _simple_foreground(arr)
    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    min_fg_per_cell = max(600, int(cell_area * 0.02))

    issues: list[str] = []
    for row, col, ys, xs in _cell_slices(fg.shape, rows=rows, cols=cols):
        cell_fg_count = int(fg[ys, xs].sum())
        if cell_fg_count < min_fg_per_cell:
            issues.append(f"R{row + 1}C{col + 1} has insufficient sprite content ({cell_fg_count} px)")

    return issues


def validate_sprite_sheet(
    image: bytes | Image.Image,
    *,
    rows: int = 3,
    cols: int = 3,
    strict_matte: bool = False,
) -> list[str]:
    arr = _image_to_rgb_array(image)

    if strict_matte:
        return _validate_strict(arr, rows=rows, cols=cols)

    return _validate_simple(arr, rows=rows, cols=cols)


def _extract_simple(arr: np.ndarray, *, rows: int, cols: int, padding: int) -> list[Image.Image]:
    fg = _simple_foreground(arr)

    if not fg.any():
        raise RuntimeError(
            "No foreground detected. Is the matte color clearly distinct "
            "from the sprites? You may want strict_matte=True for noisy inputs."
        )

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

        crop_rgb = arr[ys_cell, xs_cell][y0:y1, x0:x1]
        crop_alpha = cell_fg[y0:y1, x0:x1].astype(np.uint8) * 255
        aligned.append(Image.fromarray(np.dstack([crop_rgb, crop_alpha]), "RGBA"))

    return aligned


def _extract_strict(arr: np.ndarray, *, rows: int, cols: int, padding: int) -> list[Image.Image]:
    h, w = arr.shape[:2]
    fg, bg_candidate = _foreground_mask_from_generated_matte(arr, rows=rows, cols=cols)

    if not fg.any():
        raise RuntimeError(
            "No foreground detected. The background sampler couldn't "
            "distinguish sprites from background — does this image have "
            "a uniform border that's clearly background?"
        )

    bounds_fg = _bounds_mask_without_soft_highlights(arr, fg)
    min_component_area = max(8, int((h * w / (rows * cols)) * 0.0002))
    bounds_fg = _remove_small_components(bounds_fg, min_area=min_component_area)

    aligned: list[Image.Image] = []
    for _, _, ys_cell, xs_cell in _cell_slices(fg.shape, rows=rows, cols=cols):
        sprite_mask, size = _largest_component(fg[ys_cell, xs_cell])

        if size == 0:
            aligned.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            continue

        cell_arr = arr[ys_cell, xs_cell]
        cell_bg_cand = bg_candidate[ys_cell, xs_cell]
        cell_bounds = sprite_mask & bounds_fg[ys_cell, xs_cell]
        if not cell_bounds.any():
            cell_bounds = sprite_mask

        ys2, xs2 = np.where(cell_bounds)
        cell_h, cell_w = sprite_mask.shape
        y0 = max(0, int(ys2.min()) - padding)
        x0 = max(0, int(xs2.min()) - padding)
        y1 = min(cell_h, int(ys2.max()) + 1 + padding)
        x1 = min(cell_w, int(xs2.max()) + 1 + padding)

        crop_mask = sprite_mask[y0:y1, x0:x1] & ~_connected_to_edges(cell_bg_cand[y0:y1, x0:x1])
        if not crop_mask.any():
            crop_mask = sprite_mask[y0:y1, x0:x1]

        crop_rgb = _fill_transparent_rgb(cell_arr[y0:y1, x0:x1], crop_mask)
        alpha = crop_mask.astype(np.uint8) * 255
        aligned.append(Image.fromarray(np.dstack([crop_rgb, alpha]), "RGBA"))

    return aligned


def extract_sprites(
    image: bytes | Image.Image,
    rows: int = 3,
    cols: int = 3,
    padding: int = 8,
    *,
    strict_matte: bool = False,
) -> dict[PoseT, Image.Image]:
    arr = np.array(_to_pil(image).convert("RGB"))

    if strict_matte:
        aligned = _extract_strict(arr, rows=rows, cols=cols, padding=padding)
    else:
        aligned = _extract_simple(arr, rows=rows, cols=cols, padding=padding)

    if len(aligned) != rows * cols:
        raise RuntimeError(f"expected {rows * cols} extracted sprites, got {len(aligned)}")

    return dict(zip(PoseT, aligned, strict=True))
