from collections.abc import Iterable
import io
import random

from PIL import Image
from scipy import ndimage
import numpy as np

from app import types


def clamp(value: float, *, minimum: float, maximum: float) -> float:
    """Constraints a value within the inclusive range [minimum, maximum]."""
    return max(minimum, min(maximum, value))


def weighted_sample[T](
    population: Iterable[T],
    weights: Iterable[float],
    *,
    k: int = 1,
) -> list[T]:
    """Like random.choices, but without replacement."""
    # Convert these to lists so we can be sure that indexing and .pop() works.
    population = list(population)
    weights    = list(weights)

    if len(population) != len(weights):
        raise ValueError("population and weights must have the same length")

    if not (0 < k <= len(population)):
        raise ValueError(f"k must be between 0 and {len(population) + 1}")

    r: list[T] = []

    for s in range(k):
        i = random.choices(range(len(population)), weights=weights, k=1)[0]
        _ = weights.pop(i)
        e = population.pop(i)
        r.append(e)

    return r


def _hue_distance(hue: np.ndarray, center: float) -> np.ndarray:
    """Return circular HSV hue distance in the [0.0, 0.5] range."""
    return np.abs((hue - center + 0.5) % 1.0 - 0.5)


def _edge_pixels(arr: np.ndarray, *, border: int = 6) -> np.ndarray:
    h, w = arr.shape[:2]
    border = max(1, min(border, max(1, h // 2), max(1, w // 2)))
    edge = np.concatenate([
        arr[:border, :].reshape(-1, 3),
        arr[-border:, :].reshape(-1, 3),
        arr[:, :border].reshape(-1, 3),
        arr[:, -border:].reshape(-1, 3),
    ])

    return edge


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

    lab = rgb2lab(arr / 255.0)
    edge = _edge_pixels(arr, border=border)
    edge_lab = rgb2lab(edge.reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    edge_center = np.median(edge_lab, axis=0)
    edge_dist = np.linalg.norm(edge_lab - edge_center, axis=1)
    strict_tolerance = min(max(float(np.percentile(edge_dist, 99.5)) * 1.3 + 2, 6.0), 16.0)
    edge_candidate_tolerance = min(
        max(float(np.percentile(edge_dist, 99.7)) * 1.8 + 5, strict_tolerance + 8, 18.0),
        42.0,
    )

    dominant_bg = _dominant_background_sample_mask(arr, lab, edge_center, edge_dist)
    sample_lab = np.concatenate([edge_lab, lab[dominant_bg]]) if dominant_bg.any() else edge_lab
    center = np.median(sample_lab, axis=0)

    dist = np.linalg.norm(lab - center, axis=2)
    sample_dist = np.linalg.norm(sample_lab - center, axis=1)
    candidate_tolerance = min(
        max(float(np.percentile(sample_dist, 99.7)) * 1.8 + 5, strict_tolerance + 8, 18.0),
        42.0,
    )

    if float((dist <= candidate_tolerance).mean()) > 0.84:
        dist = np.linalg.norm(lab - edge_center, axis=2)
        candidate_tolerance = edge_candidate_tolerance

    return dist, strict_tolerance, candidate_tolerance


def _same_hue_shadow_mask(arr: np.ndarray, *, border: int = 6) -> np.ndarray:
    from skimage.color import rgb2hsv

    edge = _edge_pixels(arr, border=border)
    hsv = rgb2hsv(arr / 255.0)
    edge_hsv = rgb2hsv(edge.reshape(-1, 1, 3) / 255.0).reshape(-1, 3)

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


def _background_mask_from_edges(arr: np.ndarray, *, border: int = 6) -> np.ndarray:
    """Detect generated matte-like pixels without deciding enclosed foreground details."""
    _, candidate_bg, _ = _background_masks_from_edges(arr, border=border)

    return candidate_bg


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


def _cell_edge_connected_background(bg_candidate: np.ndarray, *, rows: int, cols: int) -> np.ndarray:
    h, w = bg_candidate.shape
    local_bg = np.zeros_like(bg_candidate, dtype=bool)

    for row in range(rows):
        y0 = int(row * h / rows)
        y1 = h if row == rows - 1 else int((row + 1) * h / rows)
        for col in range(cols):
            x0 = int(col * w / cols)
            x1 = w if col == cols - 1 else int((col + 1) * w / cols)
            crop_bg = bg_candidate[y0:y1, x0:x1]
            local_bg[y0:y1, x0:x1] |= _connected_to_edges(crop_bg)

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
    """Return a foreground mask for crop bounds that ignores soft highlight halos."""
    from skimage.color import rgb2hsv

    hsv = rgb2hsv(arr / 255.0)
    soft_highlight = (hsv[..., 1] <= 0.22) & (hsv[..., 2] >= 0.62)
    solid_support = fg & ~soft_highlight

    if not solid_support.any():
        return fg

    supported_highlight = ndimage.binary_dilation(solid_support, iterations=3) & soft_highlight
    bounds_mask = fg & (~soft_highlight | supported_highlight)

    return bounds_mask if bounds_mask.any() else fg


def _fill_small_holes(mask: np.ndarray, *, max_area: int = 256) -> np.ndarray:
    """Fill tiny enclosed matte pockets while preserving large negative space."""
    holes = ndimage.binary_fill_holes(mask) & ~mask
    labels, count = ndimage.label(holes)

    if count == 0:
        return mask

    sizes = np.bincount(labels.ravel())
    small_holes = sizes <= max_area
    small_holes[0] = False

    return mask | small_holes[labels]


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


def _cell_slices(shape: tuple[int, int], *, rows: int, cols: int) -> Iterable[tuple[int, int, slice, slice]]:
    h, w = shape

    for row in range(rows):
        y0 = int(row * h / rows)
        y1 = h if row == rows - 1 else int((row + 1) * h / rows)
        for col in range(cols):
            x0 = int(col * w / cols)
            x1 = w if col == cols - 1 else int((col + 1) * w / cols)
            yield row, col, slice(y0, y1), slice(x0, x1)


def _hex_rgb(color: object) -> tuple[int, int, int]:
    value = str(color).strip()
    if not value.startswith("#") or len(value) != 7:
        raise ValueError(f"expected #RRGGBB color, got {value!r}")

    return int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)


def _image_to_rgb_array(image: bytes | Image.Image) -> np.ndarray:
    if not isinstance(image, Image.Image):
        image = Image.open(io.BytesIO(image))

    return np.array(image.convert("RGB"))


def normalize_sprite_matte(
    image: bytes | Image.Image,
    *,
    background_color: object,
    rows: int = 3,
    cols: int = 3,
) -> bytes:
    """Replace generated matte drift with an exact key color and drop detached marks.

    Image models usually approximate the requested chroma-key color and may draw
    small floating symbols for emotion poses. Keep the largest foreground body in
    each expected cell and force all remaining pixels to the exact matte color.
    """
    arr = _image_to_rgb_array(image)
    fg, _ = _foreground_mask_from_generated_matte(arr, rows=rows, cols=cols)

    h, w = fg.shape
    cell_area = (h / rows) * (w / cols)
    min_keep_area = max(24, int(cell_area * 0.0005))
    clean_fg = np.zeros_like(fg, dtype=bool)

    for _, _, ys, xs in _cell_slices(fg.shape, rows=rows, cols=cols):
        labels, count = ndimage.label(fg[ys, xs])
        if count == 0:
            continue

        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        keep_label = int(sizes.argmax())

        if sizes[keep_label] >= min_keep_area:
            clean_fg[ys, xs] |= labels == keep_label

    clean_fg = ndimage.binary_fill_holes(clean_fg)

    normalized = arr.copy()
    normalized[~clean_fg] = _hex_rgb(background_color)

    out = io.BytesIO()
    Image.fromarray(normalized, "RGB").save(out, format="PNG")
    return out.getvalue()


def validate_sprite_sheet(image: bytes | Image.Image, *, rows: int = 3, cols: int = 3) -> list[str]:
    """Return validation issues for a generated sprite sheet.

    The check is intentionally structural: the sheet must contain one main
    foreground body per expected cell. It does not judge art quality.
    """
    arr = _image_to_rgb_array(image)
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

    for row, col, _, _ in _cell_slices(fg.shape, rows=rows, cols=cols):
        count_in_cell = int(cell_counts[row, col])
        cell_name = f"R{row + 1}C{col + 1}"

        if count_in_cell == 0:
            issues.append(f"{cell_name} has no main sprite body")
        elif count_in_cell > 1:
            issues.append(f"{cell_name} contains {count_in_cell} main sprite bodies")

    return issues


def extract_sprites(image: bytes | Image.Image, rows: int = 3, cols: int = 3, padding: int = 8) -> types.SpriteLayout:
    """Extract `rows*cols` sprites from `image` in reading order.

    Parameters
    ----------
    image : path, PIL.Image, or H×W×3 ndarray (uint8 RGB)
    rows, cols : grid shape, default 3×3
    padding : pixels of empty space around each crop, default 8

    Returns
    -------
    list of `rows*cols` PIL RGBA images in reading order
    (top-to-bottom, left-to-right). Background is transparent.
    """
    from skimage.segmentation import watershed
    from sklearn.cluster import KMeans

    if not isinstance(image, Image.Image):
        image = Image.open(io.BytesIO(image))

    arr = np.array(image.convert("RGB"))
    H, W = arr.shape[:2]

    # ---- 1. Background connectivity decides transparent background ----
    fg, bg_candidate = _foreground_mask_from_generated_matte(arr, rows=rows, cols=cols)

    # ---- 2. Solid foreground drives seeds and crop bounds -------------
    bounds_fg = _bounds_mask_without_soft_highlights(arr, fg)
    min_component_area = max(8, int((H * W / (rows * cols)) * 0.0002))
    bounds_fg = _remove_small_components(bounds_fg, min_area=min_component_area)

    if not fg.any():
        raise RuntimeError(
            "No foreground detected. The background sampler couldn't "
            "distinguish sprites from background — does this image have "
            "a uniform border that's clearly background?"
        )

    # ---- 3. K-means cluster centers (one per cell) --------------------
    seed_fg = bounds_fg if bounds_fg.any() else fg
    ys, xs = np.where(seed_fg)
    points = np.column_stack([ys, xs]).astype(np.float32)

    init = np.array(
        [[H * (r + 0.5) / rows, W * (c + 0.5) / cols]
         for r in range(rows) for c in range(cols)],
        dtype=np.float32,
    )
    km = KMeans(n_clusters=rows * cols, init=init, n_init=1, random_state=0)
    km.fit(points)
    centers = km.cluster_centers_  # (rows*cols, 2): (y, x)
    centers_int = centers.astype(int)

    # ---- 4. Seed-and-flood: each center → one labeled pixel, then
    #         watershed through fg with a flat elevation surface so
    #         expansion is purely connectivity-driven (geodesic).
    seed_img = np.zeros((H, W), dtype=np.int32)
    for i, (cy, cx) in enumerate(centers_int, start=1):
        if not seed_fg[cy, cx]:
            # Snap to nearest fg pixel — k-means centers can land in
            # background pockets for awkwardly shaped sprites.
            d = (ys - cy) ** 2 + (xs - cx) ** 2
            j = int(d.argmin())
            cy, cx = int(ys[j]), int(xs[j])
        seed_img[cy, cx] = i

    label_img = watershed(
        np.zeros((H, W), dtype=np.int32),
        markers=seed_img,
        mask=fg,
    )

    # ---- 5. Reading order: sort centers by y, chunk into `rows` rows
    #         of `cols` each, then sort each chunk by x. Robust against
    #         centers that fall near grid-boundary y values.
    by_y = sorted(range(len(centers)), key=lambda i: centers[i, 0])
    order: list[int] = []
    for r in range(rows):
        chunk = by_y[r * cols:(r + 1) * cols]
        chunk.sort(key=lambda i: centers[i, 1])
        order.extend(chunk)

    # ---- 6. Crop each label into a PIL RGBA image --------------------
    aligned: list[Image.Image] = []

    for cid in order:
        mask = (label_img == cid + 1)
        bounds_mask = mask & bounds_fg
        if not bounds_mask.any():
            bounds_mask = mask
        ys2, xs2 = np.where(bounds_mask)

        if len(ys2) == 0:
            # Empty cell — return a 1×1 fully-transparent placeholder so
            # the caller can still rely on len(aligned) == rows*cols.
            aligned.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            continue

        y0 = max(0, ys2.min() - padding)
        x0 = max(0, xs2.min() - padding)
        y1 = min(H, ys2.max() + 1 + padding)
        x1 = min(W, xs2.max() + 1 + padding)

        crop_mask = mask[y0:y1, x0:x1] & ~_connected_to_edges(bg_candidate[y0:y1, x0:x1])
        if not crop_mask.any():
            crop_mask = mask[y0:y1, x0:x1]

        crop_rgb = _fill_transparent_rgb(arr[y0:y1, x0:x1], crop_mask)
        alpha = (crop_mask.astype(np.uint8) * 255)
        rgba = np.dstack([crop_rgb, alpha])
        aligned.append(Image.fromarray(rgba, "RGBA"))
    
    sprite_layout: types.SpriteLayout = {
        "sheet": image,
        # Battle row (row 0)
        "battle_back": aligned[0],
        "battle_hero": aligned[1],
        "battle_opponent": aligned[2],
        # Idle row (row 1)
        "emote_resting": aligned[3],
        "emote_happy": aligned[4],
        "emote_frustrated": aligned[5],
        # Expressive row (row 2)
        "emote_proud": aligned[6],
        "emote_confused": aligned[7],
        "emote_sad": aligned[8],
    }

    return sprite_layout
