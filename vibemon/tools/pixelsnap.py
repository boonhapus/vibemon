# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=10"]
# ///
"""Snap AI-generated pixel-art renders onto a true low-res grid.

Generated sprites *look* like pixel art but are anti-aliased at native
resolution (1px color runs everywhere), so nearest-neighbor upscaling can
never be crisp. This tool downsamples to the real intended grid (box
average -> hard nearest pass), optionally quantizes to the locked palette
(docs/development/COLORS.md), and writes `<name>@<grid>.png` next to the
source. Display the output with `image-rendering: pixelated` at integer
multiples only.

Usage:
    uv run vibemon/tools/pixelsnap.py <image.png> --grid 128 [--palette]
    uv run vibemon/tools/pixelsnap.py <image.png> --grid 96 128 160   # candidates
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.workflows import _pixelsnap_palette, pixelsnap  # noqa: E402


def trim(image: Image.Image) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    return image.crop(bbox) if bbox else image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument(
        "--grid",
        type=int,
        nargs="+",
        default=[128],
        help="target size of the long edge, in true pixels",
    )
    parser.add_argument(
        "--palette",
        action="store_true",
        help="quantize to the locked palette",
    )
    parser.add_argument(
        "--trim",
        action="store_true",
        help="crop transparent padding after snapping",
    )
    args = parser.parse_args()

    source = Image.open(args.image)
    for grid in args.grid:
        out = pixelsnap.snap(source, grid=grid, quantize_palette=args.palette)
        if args.trim:
            out = trim(out)
        dest = args.image.with_name(f"{args.image.stem}@{grid}{args.image.suffix}")
        out.save(dest)
        print(f"{dest} ({out.width}x{out.height})")


if __name__ == "__main__":
    main()
