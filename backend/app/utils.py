from collections.abc import Iterable
import concurrent.futures
import io
import random

from PIL import Image
from scipy import ndimage
import numpy as np
# import rembg

from app import types


class RembgSessionizer:
    """
    A rembg session that loads its model on a background thread.

    Construction returns immediately; the first call to `remove()` blocks if
    the model isn't loaded yet.
    """

    def __init__(self, model_name: str) -> None:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._future = executor.submit(rembg.new_session, model_name)
        executor.shutdown(wait=False)

    def remove(self, image_bytes: bytes, **options) -> bytes:
        """Remove the background from an input image."""
        return rembg.remove(image_bytes, **options, session=self._future.result())

    def is_ready(self) -> bool:
        """True if the model has finished loading (useful for status UI)."""
        return self._future.done()


# REMBG_SESSION = RembgSessionizer("birefnet-general")


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
    from scipy import ndimage
    from skimage.color import rgb2hsv
    from skimage.segmentation import watershed
    from sklearn.cluster import KMeans

    if not isinstance(image, Image.Image):
        image = Image.open(io.BytesIO(image))

    arr = np.array(image.convert("RGB"))
    H, W = arr.shape[:2]

    # ---- 1. Background hue/sat envelope from a thin edge strip --------
    border = 6
    edge = np.concatenate([
        arr[:border, :].reshape(-1, 3), arr[-border:, :].reshape(-1, 3),
        arr[:, :border].reshape(-1, 3), arr[:, -border:].reshape(-1, 3),
    ])
    edge_hsv = rgb2hsv(edge.reshape(-1, 1, 3) / 255.0).reshape(-1, 3)
    h_lo, h_hi = np.percentile(edge_hsv[:, 0], [0.5, 99.5])
    s_lo, s_hi = np.percentile(edge_hsv[:, 1], [0.5, 99.5])
    # Pad the envelope a bit so subtle gradient banding in the interior
    # doesn't leak through as foreground specks.
    h_pad = (h_hi - h_lo) * 0.5 + 0.01
    s_pad = (s_hi - s_lo) * 0.5 + 0.02
    h_lo -= h_pad; h_hi += h_pad
    s_lo -= s_pad; s_hi += s_pad

    hsv = rgb2hsv(arr / 255.0)
    fg = ~((hsv[..., 0] >= h_lo) & (hsv[..., 0] <= h_hi) &
           (hsv[..., 1] >= s_lo) & (hsv[..., 1] <= s_hi))

    # ---- 2. Fill internal holes and clean specks ----------------------
    fg = ndimage.binary_fill_holes(fg)
    fg = ndimage.binary_opening(fg, iterations=2)
    fg = ndimage.binary_closing(fg, iterations=2)
    fg = ndimage.binary_fill_holes(fg)

    if not fg.any():
        raise RuntimeError(
            "No foreground detected. The background sampler couldn't "
            "distinguish sprites from background — does this image have "
            "a uniform border that's clearly background?"
        )

    # ---- 3. K-means cluster centers (one per cell) --------------------
    ys, xs = np.where(fg)
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
        if not fg[cy, cx]:
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
        ys2, xs2 = np.where(mask)

        if len(ys2) == 0:
            # Empty cell — return a 1×1 fully-transparent placeholder so
            # the caller can still rely on len(aligned) == rows*cols.
            aligned.append(Image.new("RGBA", (1, 1), (0, 0, 0, 0)))
            continue

        y0 = max(0, ys2.min() - padding)
        x0 = max(0, xs2.min() - padding)
        y1 = min(H, ys2.max() + 1 + padding)
        x1 = min(W, xs2.max() + 1 + padding)

        crop_rgb = arr[y0:y1, x0:x1]
        alpha = (mask[y0:y1, x0:x1].astype(np.uint8) * 255)
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
