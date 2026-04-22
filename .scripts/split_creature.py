# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "pillow", "rembg[gpu]", "onnxruntime"]
# ///
"""
Split a 3-panel creature sheet into individual transparent-background renders.

Usage:
    python split_creature_v2.py --image gemini.png
    python split_creature_v2.py --image gemini.png --output-dir out/ --model isnet-anime

Models (best to good):
    birefnet-general   general-purpose, strongest edges   (default)
    isnet-anime        tuned for illustrated/anime art
    u2net              fast, slightly lower quality
"""
from __future__ import annotations

import argparse
import pathlib

import numpy as np
from PIL import Image
from rembg import new_session, remove


PANEL_NAMES = ("left", "center", "right")
DEFAULT_MODEL = "birefnet-general"
DIVIDER_SEARCH_RADIUS = 80


def _sample_bg_color(arr: np.ndarray, patch: int = 16) -> tuple[int, int, int]:
    """Median RGB from the four corner patches."""
    h, w = arr.shape[:2]
    s = min(patch, h // 4, w // 4)
    samples = np.concatenate([
        arr[:s,  :s,    :3].reshape(-1, 3),
        arr[:s,  w-s:,  :3].reshape(-1, 3),
        arr[h-s:, :s,   :3].reshape(-1, 3),
        arr[h-s:, w-s:, :3].reshape(-1, 3),
    ])
    m = np.median(samples, axis=0).astype(np.uint8)
    return (int(m[0]), int(m[1]), int(m[2]))


def _find_dividers(arr: np.ndarray, bg: tuple[int, int, int]) -> tuple[int, int]:
    """
    Find the two vertical divider columns by peak color-deviation from bg
    in a search window around the expected 1/3 and 2/3 positions.
    """
    w = arr.shape[1]
    bg_f = np.array(bg, dtype=np.float32)
    col_mean = arr[:, :, :3].astype(np.float32).mean(axis=0)      # (W, 3)
    col_diff = np.sqrt(((col_mean - bg_f) ** 2).sum(axis=1))       # (W,)

    dividers = []
    for frac in (1 / 3, 2 / 3):
        center = int(round(w * frac))
        lo, hi = max(0, center - DIVIDER_SEARCH_RADIUS), min(w, center + DIVIDER_SEARCH_RADIUS)
        best = lo + int(np.argmax(col_diff[lo:hi]))
        # Fall back to mathematical third if nothing stands out
        if col_diff[best] < np.median(col_diff[lo:hi]) * 2 + 1:
            best = center
        dividers.append(best)

    return dividers[0], dividers[1]


def _pad_to_size(image: Image.Image, width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    canvas.paste(image, ((width - image.width) // 2, (height - image.height) // 2), image)
    return canvas


def split_creature(
    image_path: pathlib.Path,
    output_dir: pathlib.Path,
    model: str = DEFAULT_MODEL,
) -> None:
    image = Image.open(image_path).convert("RGBA")
    arr = np.array(image.convert("RGB"))

    bg = _sample_bg_color(arr)
    print(f"Background: rgb{bg} (#{bg[0]:02X}{bg[1]:02X}{bg[2]:02X})")

    div1, div2 = _find_dividers(arr, bg)
    print(f"Dividers at columns: {div1}, {div2}")

    panel_bounds = [(0, div1), (div1 + 1, div2), (div2 + 1, image.width)]

    print(f"Loading rembg model: {model} ...")
    session = new_session(model)

    output_dir.mkdir(parents=True, exist_ok=True)
    panels: dict[str, Image.Image] = {}

    for name, (x0, x1) in zip(PANEL_NAMES, panel_bounds):
        print(f"Processing panel: {name}")
        panel = image.crop((x0, 0, x1, image.height))
        panel = remove(panel, session=session)

        # Tight-crop to non-transparent pixels
        bbox = panel.getchannel("A").getbbox()
        if bbox:
            panel = panel.crop(bbox)

        panels[name] = panel

    # Uniform canvas size across all three panels
    max_w = max(p.width  for p in panels.values())
    max_h = max(p.height for p in panels.values())

    for name, panel in panels.items():
        out = _pad_to_size(panel, max_w, max_h)
        path = output_dir / f"{name}.png"
        out.save(path, optimize=True)
        print(f"Saved {path}  ({max_w}×{max_h})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a 3-panel creature sheet into transparent PNGs using neural segmentation."
    )
    parser.add_argument("--image",      type=pathlib.Path, required=True, help="Source image path.")
    parser.add_argument("--output-dir", type=pathlib.Path, default=None,  help="Output directory (default: image folder).")
    parser.add_argument("--model",      default=DEFAULT_MODEL,            help=f"rembg model name (default: {DEFAULT_MODEL}).")
    args = parser.parse_args()

    split_creature(
        args.image,
        output_dir=args.output_dir or args.image.parent,
        model=args.model,
    )


if __name__ == "__main__":
    main()