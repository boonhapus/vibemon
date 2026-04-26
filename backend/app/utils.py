import io

from PIL import Image
import numpy as np
import rembg

from app import types

REMBG_SESSION = rembg.new_session("birefnet-general")


def clamp(value: int, *, minimum: int, maximum: int) -> int:
    """Ensure value is between minimum and maximum."""
    return max(minimum, min(maximum, value))


def extract_sprites(sprite_sheet: bytes) -> types.SpriteLayout:
    """Split a horizontal sheet of three sprites into three same-sized images.

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

    # SPRITE_NAMES = ("perspective_player", "showcase", "opponent_perspective")
    # SPRITE_NAMES = list(types.SpriteLayout.__annotations__.keys())

    # 1. Strip the background so only sprite pixels remain opaque.
    transparent_bytes = rembg.remove(sprite_sheet, session=REMBG_SESSION)
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
