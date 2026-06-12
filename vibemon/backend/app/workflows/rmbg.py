"""Connected background removal for generated sprite mattes."""

from collections import deque
import io

from PIL import Image
import numpy as np
import numpy.typing as npt

BoolMask = npt.NDArray[np.bool_]
ImageArray = npt.NDArray[np.int16]
FloatArray = npt.NDArray[np.floating]
DistanceMap = npt.NDArray[np.float64]
ColorVector = npt.NDArray[np.floating]

FOUR_NEIGHBORS: tuple[tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))
EIGHT_NEIGHBORS: tuple[tuple[int, int], ...] = (
    *FOUR_NEIGHBORS,
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
)


def sample_border_background(image: ImageArray) -> ColorVector:
    """Median RGB of the one-pixel image border."""
    border_pixels = np.concatenate(
        [image[0, :], image[-1, :], image[:, 0], image[:, -1]],
        axis=0,
    )
    return np.median(border_pixels, axis=0)


def compute_background_distance(
    image: FloatArray,
    background_color: ColorVector,
    luminance_weight: float,
) -> DistanceMap:
    """Hue-weighted L1 distance from every pixel to the background color."""
    red_minus_green = image[..., 0] - image[..., 1]
    green_minus_blue = image[..., 1] - image[..., 2]
    luminance = image.mean(axis=2)

    bg_red_minus_green = background_color[0] - background_color[1]
    bg_green_minus_blue = background_color[1] - background_color[2]
    bg_luminance = float(background_color.mean())

    return (
        np.abs(red_minus_green - bg_red_minus_green)
        + np.abs(green_minus_blue - bg_green_minus_blue)
        + luminance_weight * np.abs(luminance - bg_luminance)
    )


def otsu_threshold(values: npt.NDArray[np.integer], max_value: int) -> int:
    """Otsu threshold splitting low-distance background from high-distance subject."""
    histogram = np.bincount(
        np.clip(values, 0, max_value).ravel(),
        minlength=max_value + 1,
    ).astype(np.float64)
    weight_below = np.cumsum(histogram)
    weight_above = histogram.sum() - weight_below

    cumulative_mean = np.cumsum(histogram * np.arange(max_value + 1))
    total_mean = cumulative_mean[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean_below = cumulative_mean / weight_below
        mean_above = (total_mean - cumulative_mean) / weight_above
        between_class_variance = weight_below * weight_above * (mean_below - mean_above) ** 2
    between_class_variance[np.isnan(between_class_variance)] = 0
    return int(np.argmax(between_class_variance))


def make_border_ring(height: int, width: int) -> BoolMask:
    ring = np.zeros((height, width), dtype=bool)
    ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
    return ring


def flood_fill_background(
    image: ImageArray,
    distance_map: DistanceMap,
    step_tolerance: int,
    band: int,
) -> BoolMask:
    height, width, _ = image.shape
    is_background: BoolMask = np.zeros((height, width), dtype=bool)
    frontier: deque[tuple[int, int]] = deque()

    def enqueue(row: int, col: int) -> None:
        if not is_background[row, col]:
            is_background[row, col] = True
            frontier.append((row, col))

    for col in range(width):
        enqueue(0, col)
        enqueue(height - 1, col)
    for row in range(height):
        enqueue(row, 0)
        enqueue(row, width - 1)

    while frontier:
        row, col = frontier.popleft()
        source_color = image[row, col]
        for d_row, d_col in FOUR_NEIGHBORS:
            n_row, n_col = row + d_row, col + d_col
            if not (0 <= n_row < height and 0 <= n_col < width):
                continue
            if is_background[n_row, n_col]:
                continue
            within_band = distance_map[n_row, n_col] <= band
            step = int(np.abs(image[n_row, n_col] - source_color).sum())
            if within_band and step <= step_tolerance:
                is_background[n_row, n_col] = True
                frontier.append((n_row, n_col))
    return is_background


def dilate(mask: BoolMask) -> BoolMask:
    height, width = mask.shape
    grown = np.zeros((height, width), dtype=bool)
    grown[1:, :] |= mask[:-1, :]
    grown[:-1, :] |= mask[1:, :]
    grown[:, 1:] |= mask[:, :-1]
    grown[:, :-1] |= mask[:, 1:]
    return grown


def sweep_pockets(
    distance_map: DistanceMap,
    band: int,
    known_background: BoolMask,
) -> BoolMask:
    height, width = distance_map.shape
    near_background = distance_map <= band
    reached: BoolMask = np.zeros((height, width), dtype=bool)
    frontier: deque[tuple[int, int]] = deque()

    adjacent_to_known = dilate(known_background)
    start_pixels = near_background & (adjacent_to_known | make_border_ring(height, width))
    start_rows, start_cols = np.nonzero(start_pixels)
    for row, col in zip(start_rows.tolist(), start_cols.tolist(), strict=True):
        if not reached[row, col]:
            reached[row, col] = True
            frontier.append((row, col))

    while frontier:
        row, col = frontier.popleft()
        for d_row, d_col in FOUR_NEIGHBORS:
            n_row, n_col = row + d_row, col + d_col
            if (
                0 <= n_row < height
                and 0 <= n_col < width
                and not reached[n_row, n_col]
                and near_background[n_row, n_col]
            ):
                reached[n_row, n_col] = True
                frontier.append((n_row, n_col))
    return known_background | reached


def recover_enclosed_pockets(
    distance_map: DistanceMap,
    band: int,
    tight_gate: int,
    min_pocket_size: int,
    background_mask: BoolMask,
) -> BoolMask:
    if tight_gate <= 0:
        return background_mask

    height, width = distance_map.shape
    near_exact = (~background_mask) & (distance_map <= tight_gate)
    near_background = distance_map <= band
    background_or_near_exact = background_mask | near_exact

    reachable_from_border: BoolMask = np.zeros((height, width), dtype=bool)
    frontier: deque[tuple[int, int]] = deque()

    def seed_if_open(row: int, col: int) -> None:
        if background_or_near_exact[row, col] and not reachable_from_border[row, col]:
            reachable_from_border[row, col] = True
            frontier.append((row, col))

    for col in range(width):
        seed_if_open(0, col)
        seed_if_open(height - 1, col)
    for row in range(height):
        seed_if_open(row, 0)
        seed_if_open(row, width - 1)

    while frontier:
        row, col = frontier.popleft()
        for d_row, d_col in FOUR_NEIGHBORS:
            n_row, n_col = row + d_row, col + d_col
            if (
                0 <= n_row < height
                and 0 <= n_col < width
                and background_or_near_exact[n_row, n_col]
                and not reachable_from_border[n_row, n_col]
            ):
                reachable_from_border[n_row, n_col] = True
                frontier.append((n_row, n_col))

    enclosed_cores = near_exact & ~reachable_from_border

    recovered: BoolMask = np.zeros((height, width), dtype=bool)
    frontier = deque()
    core_rows, core_cols = np.nonzero(enclosed_cores)
    for row, col in zip(core_rows.tolist(), core_cols.tolist(), strict=True):
        if not recovered[row, col]:
            recovered[row, col] = True
            frontier.append((row, col))

    while frontier:
        row, col = frontier.popleft()
        for d_row, d_col in FOUR_NEIGHBORS:
            n_row, n_col = row + d_row, col + d_col
            if (
                0 <= n_row < height
                and 0 <= n_col < width
                and not recovered[n_row, n_col]
                and near_background[n_row, n_col]
                and not background_mask[n_row, n_col]
            ):
                recovered[n_row, n_col] = True
                frontier.append((n_row, n_col))

    if min_pocket_size > 1 and recovered.any():
        recovered = drop_small_components(recovered, min_pocket_size)
    return background_mask | recovered


def drop_small_components(mask: BoolMask, min_size: int) -> BoolMask:
    height, width = mask.shape
    kept: BoolMask = np.zeros((height, width), dtype=bool)
    visited: BoolMask = np.zeros((height, width), dtype=bool)

    for start_row in range(height):
        for start_col in range(width):
            if not mask[start_row, start_col] or visited[start_row, start_col]:
                continue
            component: list[tuple[int, int]] = []
            frontier: deque[tuple[int, int]] = deque([(start_row, start_col)])
            visited[start_row, start_col] = True
            while frontier:
                row, col = frontier.popleft()
                component.append((row, col))
                for d_row, d_col in FOUR_NEIGHBORS:
                    n_row, n_col = row + d_row, col + d_col
                    if 0 <= n_row < height and 0 <= n_col < width and mask[n_row, n_col] and not visited[n_row, n_col]:
                        visited[n_row, n_col] = True
                        frontier.append((n_row, n_col))
            if len(component) >= min_size:
                for row, col in component:
                    kept[row, col] = True
    return kept


def keep_largest_component(foreground_mask: BoolMask) -> BoolMask:
    height, width = foreground_mask.shape
    labels = np.zeros((height, width), dtype=np.int32)
    current_label = 0
    component_size: dict[int, int] = {}

    for start_row in range(height):
        for start_col in range(width):
            if not foreground_mask[start_row, start_col] or labels[start_row, start_col] != 0:
                continue
            current_label += 1
            size = 0
            frontier: deque[tuple[int, int]] = deque([(start_row, start_col)])
            labels[start_row, start_col] = current_label
            while frontier:
                row, col = frontier.popleft()
                size += 1
                for d_row, d_col in EIGHT_NEIGHBORS:
                    n_row, n_col = row + d_row, col + d_col
                    if (
                        0 <= n_row < height
                        and 0 <= n_col < width
                        and foreground_mask[n_row, n_col]
                        and labels[n_row, n_col] == 0
                    ):
                        labels[n_row, n_col] = current_label
                        frontier.append((n_row, n_col))
            component_size[current_label] = size

    if not component_size:
        return foreground_mask
    largest_label = max(component_size, key=lambda label: component_size[label])
    return labels == largest_label


def find_edge_pixels(mask: BoolMask) -> BoolMask:
    edge: BoolMask = np.zeros_like(mask)
    edge[1:, :] |= mask[1:, :] & ~mask[:-1, :]
    edge[:-1, :] |= mask[:-1, :] & ~mask[1:, :]
    edge[:, 1:] |= mask[:, 1:] & ~mask[:, :-1]
    edge[:, :-1] |= mask[:, :-1] & ~mask[:, 1:]
    return edge


def defringe(
    image: ImageArray,
    foreground_mask: BoolMask,
    passes: int,
    match_tolerance: int,
) -> BoolMask:
    height, width, _ = image.shape
    rgb = image[..., :3].astype(np.float32)

    for _ in range(passes):
        background_mask = ~foreground_mask
        boundary = find_edge_pixels(foreground_mask)

        neighbor_color_sum = np.zeros((height, width, 3), dtype=np.float32)
        neighbor_count = np.zeros((height, width), dtype=np.float32)
        for d_row, d_col in EIGHT_NEIGHBORS:
            shifted_is_bg = np.zeros((height, width), dtype=bool)
            shifted_rgb = np.zeros((height, width, 3), dtype=np.float32)
            dst_rows = slice(max(0, d_row), height + min(0, d_row))
            dst_cols = slice(max(0, d_col), width + min(0, d_col))
            src_rows = slice(max(0, -d_row), height + min(0, -d_row))
            src_cols = slice(max(0, -d_col), width + min(0, -d_col))
            shifted_is_bg[dst_rows, dst_cols] = background_mask[src_rows, src_cols]
            shifted_rgb[dst_rows, dst_cols] = rgb[src_rows, src_cols]
            neighbor_count += shifted_is_bg
            neighbor_color_sum += shifted_rgb * shifted_is_bg[..., None]

        has_background_neighbor = neighbor_count > 0
        local_background = np.zeros_like(neighbor_color_sum)
        local_background[has_background_neighbor] = (
            neighbor_color_sum[has_background_neighbor] / neighbor_count[has_background_neighbor, None]
        )
        distance_to_local_bg = np.abs(rgb - local_background).sum(axis=2)

        fringe = boundary & has_background_neighbor & (distance_to_local_bg <= match_tolerance)
        if not fringe.any():
            break
        foreground_mask = foreground_mask & ~fringe
    return foreground_mask


def remove_connected_background(
    image: ImageArray,
    *,
    background_color: ColorVector | None = None,
    step_tolerance: int = 26,
    band: int | None = None,
    luminance_weight: float = 0.35,
    seep_tight: int = 15,
    seep_min: int = 10,
    fringe_passes: int = 2,
    fringe_tol: int = 60,
    keep_specks: bool = False,
) -> BoolMask:
    """Return a foreground mask for an RGB image array."""
    if background_color is None:
        background_color = sample_border_background(image)

    distance_map = compute_background_distance(
        image.astype(np.float32),
        background_color.astype(np.float32),
        luminance_weight,
    )
    effective_band = (
        band
        if band is not None
        else otsu_threshold(
            distance_map.astype(np.int32),
            int(distance_map.max()),
        )
    )

    background_mask = flood_fill_background(image, distance_map, step_tolerance, effective_band)
    background_mask = sweep_pockets(distance_map, effective_band, background_mask)
    background_mask = recover_enclosed_pockets(
        distance_map,
        effective_band,
        min(seep_tight, effective_band),
        seep_min,
        background_mask,
    )

    foreground_mask = ~background_mask
    if not keep_specks:
        foreground_mask = keep_largest_component(foreground_mask)
    if fringe_passes > 0:
        foreground_mask = defringe(image, foreground_mask, fringe_passes, fringe_tol)
    return foreground_mask


_MATTE_MISMATCH_DISTANCE = 18.0


def _corner_pixels(rgb: np.ndarray) -> np.ndarray:
    height, width = rgb.shape[:2]
    if height < 3 or width < 3:
        return rgb.reshape(-1, 3)
    offset = max(1, min(5, height // 20, width // 20))
    return np.stack(
        [
            rgb[offset, offset],
            rgb[offset, width - 1 - offset],
            rgb[height - 1 - offset, offset],
            rgb[height - 1 - offset, width - 1 - offset],
        ]
    )


def sample_corner_background(rgb: np.ndarray) -> tuple[int, int, int]:
    samples = _corner_pixels(rgb)
    mean = samples.mean(0)
    return int(mean[0]), int(mean[1]), int(mean[2])


def rgb_to_lab_array(rgb: np.ndarray) -> np.ndarray:
    """Vectorized sRGB to CIELAB (D65) for uint8 or float RGB arrays."""
    rgb01 = np.asarray(rgb, dtype=np.float64)
    if rgb01.max() > 1.0:
        rgb01 = rgb01 / 255.0

    linear = np.where(
        rgb01 <= 0.04045,
        rgb01 / 12.92,
        ((rgb01 + 0.055) / 1.055) ** 2.4,
    )
    red, green, blue = linear[..., 0], linear[..., 1], linear[..., 2]
    x = 0.4124564 * red + 0.3575761 * green + 0.1804375 * blue
    y = 0.2126729 * red + 0.7151522 * green + 0.0721750 * blue
    z = 0.0193339 * red + 0.1191920 * green + 0.9503041 * blue
    x /= 0.95047
    y /= 1.0
    z /= 1.08883

    delta = (6.0 / 29.0) ** 3
    delta_inv = 3 * (6.0 / 29.0) ** 2
    delta_offset = (6.0 / 29.0) + 4 / 29

    def _f(channel: np.ndarray) -> np.ndarray:
        return np.where(channel > delta, np.cbrt(channel), channel / delta_inv + delta_offset)

    fx, fy, fz = _f(x), _f(y), _f(z)
    return np.stack([116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)], axis=-1).astype(np.float32)


def lab_distance_to_matte(rgb: np.ndarray, matte_rgb: np.ndarray) -> np.ndarray:
    lab = rgb_to_lab_array(rgb)
    matte_lab = rgb_to_lab_array(np.asarray(matte_rgb, dtype=np.float32).reshape(1, 1, 3))
    return np.sqrt(((lab - matte_lab) ** 2).sum(-1))


def resolve_background_color(
    image: Image.Image,
    bg_color: tuple[int, int, int] | None,
) -> tuple[int, int, int]:
    """Pick the chroma-key color for ``image``.

    Image models often ignore the requested matte and paint a different flat
    wash. When corner pixels are closer to each other than to the stored matte,
    sample the corners instead of forcing the stored value.
    """
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    detected = sample_corner_background(rgb)
    if bg_color is None:
        return detected

    corner_samples = _corner_pixels(rgb)
    stored_dist = float(lab_distance_to_matte(corner_samples, np.array(bg_color, dtype=np.float32)).mean())
    detected_dist = float(lab_distance_to_matte(corner_samples, np.array(detected, dtype=np.float32)).mean())
    if stored_dist > _MATTE_MISMATCH_DISTANCE and detected_dist + 1.0 < stored_dist:
        return detected
    return bg_color


def snap_painted_matte(
    image: bytes | Image.Image,
    *,
    stored_matte: tuple[int, int, int],
    step_tolerance: int = 26,
    luminance_weight: float = 0.35,
    seep_tight: int = 15,
    seep_min: int = 10,
) -> Image.Image:
    """Rewrite a model-painted background wash to the stored chroma-key color."""
    source = to_pil(image).convert("RGB")
    rgb = np.asarray(source, dtype=np.int16)
    painted = np.array(sample_corner_background(rgb.astype(np.float32)), dtype=np.float64)
    painted_dist = compute_background_distance(
        rgb.astype(np.float32),
        painted,
        luminance_weight,
    )
    effective_band = otsu_threshold(
        painted_dist.astype(np.int32),
        int(painted_dist.max()),
    )
    background_mask = flood_fill_background(rgb, painted_dist, step_tolerance, effective_band)
    background_mask = sweep_pockets(painted_dist, effective_band, background_mask)
    background_mask = recover_enclosed_pockets(
        painted_dist,
        effective_band,
        min(seep_tight, effective_band),
        seep_min,
        background_mask,
    )

    snapped = rgb.copy()
    snapped[background_mask] = np.array(stored_matte, dtype=np.int16)
    return Image.fromarray(np.clip(snapped, 0, 255).astype(np.uint8), "RGB")


def _binary_fill_holes(mask: BoolMask) -> BoolMask:
    """Fill enclosed holes in a boolean mask by flooding in from the border."""
    height, width = mask.shape
    outside: BoolMask = np.zeros((height, width), dtype=bool)
    frontier: deque[tuple[int, int]] = deque()

    def enqueue_outside(row: int, col: int) -> None:
        if not outside[row, col] and not mask[row, col]:
            outside[row, col] = True
            frontier.append((row, col))

    for col in range(width):
        enqueue_outside(0, col)
        enqueue_outside(height - 1, col)
    for row in range(height):
        enqueue_outside(row, 0)
        enqueue_outside(row, width - 1)

    while frontier:
        row, col = frontier.popleft()
        for d_row, d_col in FOUR_NEIGHBORS:
            n_row, n_col = row + d_row, col + d_col
            if 0 <= n_row < height and 0 <= n_col < width and not outside[n_row, n_col] and not mask[n_row, n_col]:
                outside[n_row, n_col] = True
                frontier.append((n_row, n_col))

    return mask | ~outside


def punch_enclosed_matte_holes(
    image: bytes | Image.Image,
    *,
    stored_matte: tuple[int, int, int],
    lab_threshold: float = 12.0,
    opaque_threshold: int = 128,
) -> Image.Image:
    """Clear chroma-key-colored pockets trapped inside a keyed sprite silhouette."""
    rgba = to_pil(image).convert("RGBA")
    arr = np.asarray(rgba)
    rgb = arr[..., :3]
    alpha = arr[..., 3]

    matte_lab = lab_distance_to_matte(rgb, np.array(stored_matte, dtype=np.uint8).reshape(1, 1, 3))
    opaque = alpha >= opaque_threshold
    real_foreground = opaque & (matte_lab > lab_threshold)
    filled_foreground = _binary_fill_holes(real_foreground)
    enclosed_matte = filled_foreground & ~real_foreground & opaque

    if enclosed_matte.any():
        arr = arr.copy()
        arr[enclosed_matte, 3] = 0
    return Image.fromarray(arr, "RGBA")


def to_pil(image: bytes | Image.Image) -> Image.Image:
    """Decode PNG/JPEG bytes or pass through an existing PIL image."""
    return image if isinstance(image, Image.Image) else Image.open(io.BytesIO(image))


def key_sprite(
    image: bytes | Image.Image,
    bg_color: tuple[int, int, int] | None = None,
    *,
    step_tolerance: int = 26,
    band: int | None = None,
    luminance_weight: float = 0.35,
    seep_tight: int = 15,
    seep_min: int = 10,
    fringe_passes: int = 2,
    fringe_tol: int = 60,
    keep_specks: bool = False,
    despill: bool = False,
    ignore_existing_alpha: bool = False,
) -> Image.Image:
    """Remove a connected matte background and return an RGBA sprite."""
    source = to_pil(image)
    existing_alpha: np.ndarray | None = None
    if source.mode == "RGBA" and not ignore_existing_alpha:
        rgba_arr = np.asarray(source, dtype=np.float32)
        existing_alpha = rgba_arr[..., 3] / 255.0
        rgb = rgba_arr[..., :3]
    else:
        rgb = np.asarray(source.convert("RGB"), dtype=np.float32)

    matte = np.array(resolve_background_color(source, bg_color), dtype=np.float64)
    rgb_int16 = np.clip(rgb, 0.0, 255.0).astype(np.int16)
    foreground_mask = remove_connected_background(
        rgb_int16,
        background_color=matte,
        step_tolerance=step_tolerance,
        band=band,
        luminance_weight=luminance_weight,
        seep_tight=seep_tight,
        seep_min=seep_min,
        fringe_passes=fringe_passes,
        fringe_tol=fringe_tol,
        keep_specks=keep_specks,
    )
    alpha = np.where(foreground_mask, 1.0, 0.0).astype(np.float32)

    if existing_alpha is not None:
        alpha = np.clip(existing_alpha * alpha, 0.0, 1.0)

    if despill:
        rgb = np.clip(rgb - matte * (1.0 - alpha)[..., None], 0.0, 255.0)

    rgba = np.dstack([rgb, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")
