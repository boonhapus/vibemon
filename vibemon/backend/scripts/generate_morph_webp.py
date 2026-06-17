"""Build a looping morph-style animated WebP from monstore reference sprites."""

from __future__ import annotations

from pathlib import Path
import argparse
import random

from PIL import Image
import numpy as np

CANVAS = 400
CONTENT_BOX = (32, 72, 367, 375)
BOX_W = CONTENT_BOX[2] - CONTENT_BOX[0] + 1
BOX_H = CONTENT_BOX[3] - CONTENT_BOX[1] + 1
FRAMES_PER_MON = 40
CROSSFADE_START = 33
FRAME_DURATION_MS = 40
HOLD_DURATION_MS = CROSSFADE_START * FRAME_DURATION_MS


def _discover_references(monstore_root: Path) -> list[Path]:
    refs = sorted(monstore_root.glob("*/v1/r*/sprite/reference.png"))
    if not refs:
        raise SystemExit(f"No reference.png files under {monstore_root}")
    return refs


def _composite_sprite(ref_path: Path) -> Image.Image:
    source = Image.open(ref_path).convert("RGBA")
    alpha = np.asarray(source)[..., 3]
    opaque = alpha > 10
    if not opaque.any():
        raise ValueError(f"No opaque pixels in {ref_path}")

    ys, xs = np.where(opaque)
    crop = source.crop((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
    crop_w, crop_h = crop.size
    scale = min(BOX_W / crop_w, BOX_H / crop_h)
    width = max(1, round(crop_w * scale))
    height = max(1, round(crop_h * scale))
    scaled = crop.resize((width, height), Image.NEAREST)

    canvas = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    x = CONTENT_BOX[0] + (BOX_W - width) // 2
    y = CONTENT_BOX[3] - height + 1
    canvas.alpha_composite(scaled, (x, y))
    return canvas


def _blend(a: np.ndarray, b: np.ndarray, t: float) -> Image.Image:
    mixed = np.clip((1.0 - t) * a.astype(np.float64) + t * b.astype(np.float64), 0, 255)
    return Image.fromarray(mixed.astype(np.uint8), mode="RGBA")


def build_timeline(sprites: list[np.ndarray]) -> tuple[list[Image.Image], list[int]]:
    """Return unique frames and per-frame durations matching morph.webp timing."""
    count = len(sprites)
    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(count):
        current = sprites[index]
        nxt = sprites[(index + 1) % count]
        frames.append(Image.fromarray(current, mode="RGBA"))
        durations.append(HOLD_DURATION_MS)
        for frame in range(CROSSFADE_START, FRAMES_PER_MON):
            t = (frame - CROSSFADE_START) / (FRAMES_PER_MON - CROSSFADE_START)
            frames.append(_blend(current, nxt, t))
            durations.append(FRAME_DURATION_MS)
    return frames, durations


def generate_morph_webp(
    *,
    monstore_root: Path,
    output_path: Path,
    count: int = 10,
    seed: int | None = None,
) -> list[Path]:
    refs = _discover_references(monstore_root)
    if count > len(refs):
        raise SystemExit(f"Requested {count} mons but only {len(refs)} references exist.")

    rng = random.Random(seed)
    picked = rng.sample(refs, count)
    sprites = [np.asarray(_composite_sprite(path), dtype=np.uint8) for path in picked]
    frames, durations = build_timeline(sprites)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        quality=90,
        method=6,
    )
    return picked


def main() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--monstore",
        type=Path,
        default=repo_root / ".generated" / "monstore" / "mons",
        help="Root directory containing monstore mon folders.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo_root / "docs" / "public" / "morph-store.webp",
        help="Output animated WebP path.",
    )
    parser.add_argument("--count", type=int, default=10, help="Number of mons to include.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for mon selection.")
    args = parser.parse_args()

    picked = generate_morph_webp(
        monstore_root=args.monstore,
        output_path=args.output,
        count=args.count,
        seed=args.seed,
    )
    timeline_ms = len(picked) * FRAMES_PER_MON * FRAME_DURATION_MS
    print(f"Wrote {args.output} ({len(picked) * 8} unique frames, {timeline_ms} ms loop)")
    for path in picked:
        print(f"  {path.parents[3].name}")


if __name__ == "__main__":
    main()
