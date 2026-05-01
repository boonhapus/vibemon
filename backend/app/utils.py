from collections.abc import Iterable
import concurrent.futures
import io
import random

from PIL import Image
import numpy as np
import rembg

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


REMBG_SESSION = RembgSessionizer("birefnet-general")


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


def extract_sprites(sprite_sheet: bytes) -> types.SpriteLayout:
    """
    Split a horizontal sheet of three sprites into three same-sized images.

    The three output images share dimensions; each sprite is anchored at the
    bottom-center of its canvas so they stand on a common floor.
    """
    # Alpha values at or below this are treated as transparent. Background removers
    # often leave a faint halo of nearly-invisible pixels; this threshold tells those
    # apart from real sprite pixels.
    ALPHA_NOISE_FLOOR = 16

    # Two stretches of sprite pixels separated by less than this fraction of the sheet's
    # width are merged into one. Catches the case where the remover briefly disconnects
    # a held item (a leaf, a tool) from the sprite's body.
    HELD_ITEM_GAP_FRACTION = 1 / 40

    # 1. Strip the background so only sprite pixels remain opaque.
    transparent_bytes = REMBG_SESSION.remove(sprite_sheet)
    sheet = Image.open(io.BytesIO(transparent_bytes)).convert("RGBA")

    if sheet.getbbox() is None:
        raise ValueError("rembg stripped the whole image — nothing to split.")

    # 2. For each column, ask: does it contain any sprite pixel?
    alpha = np.array(sheet)[:, :, 3]
    column_has_sprite = (alpha > ALPHA_NOISE_FLOOR).any(axis=0)

    # 3. Walk left-to-right, recording each [start, end) stretch of sprite columns.
    #    Each stretch is one sprite — or one piece of one.
    stretches: list[list[int]] = []
    start = None

    for x, has_sprite in enumerate(column_has_sprite):
        if has_sprite and start is None:
            start = x

        elif not has_sprite and start is not None:
            stretches.append([start, x])
            start = None

    if start is not None:
        stretches.append([start, sheet.width])

    # 4. Bridge stretches separated by tiny gaps (held-item reattachment).
    gap = int(sheet.width * HELD_ITEM_GAP_FRACTION)
    merged: list[list[int]] = []

    for s in stretches:
        if merged and s[0] - merged[-1][1] < gap:
            merged[-1][1] = s[1]

        else:
            merged.append(s)

    # 5. Coerce to exactly three stretches.
    match len(merged):
        case 3:
            pass
        
        # Keep the three widest, then re-sort left-to-right.
        case n if n > 3:
            merged = sorted(merged, key=lambda s: s[1] - s[0], reverse=True)[:3]
            merged.sort(key=lambda s: s[0])
        
        # Couldn't tell them apart — slice the overall subject area into equal thirds
        # as a last resort.
        case _:
            left, _, right, _ = sheet.getbbox()
            slice_w = (right - left) // 3
            merged = [[left + i * slice_w, left + (i + 1) * slice_w] for i in range(3)]

    # 6. Tight-crop each sprite from its column band.
    cropped: list[Image.Image] = []

    for left, right in merged:
        band = sheet.crop((left, 0, right, sheet.height))
        inner = band.getbbox()
        cropped.append(band.crop(inner) if inner else band)

    # 7. Paste each sprite onto a common-size canvas, anchored bottom-center.
    canvas_w = max(s.width for s in cropped)
    canvas_h = max(s.height for s in cropped)
    aligned: list[Image.Image] = []

    for sprite in cropped:
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        x = (canvas_w - sprite.width) // 2
        y = canvas_h - sprite.height
        canvas.paste(sprite, (x, y))
        aligned.append(canvas)
    
    sprite_layout: types.SpriteLayout = {
        "sheet": sheet,
        "perspective_player": aligned[0],
        "perspective_opponent": aligned[2],
        "showcase": aligned[1],
    }

    return sprite_layout
