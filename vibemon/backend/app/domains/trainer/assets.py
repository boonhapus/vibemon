"""Trainer presentation asset slots and reference chroma-key helpers."""

from typing import Final
import enum
import io

from PIL import Image
import numpy as np

from app.domains.vibemon import brand


class TrainerAssetKind(enum.StrEnum):
    """Presentation asset slots for a Trainer."""

    REFERENCE = "sprite/reference.png"
    REFERENCE_RAW = "sprite/reference-raw.png"


# Canonical trainer.png fills the solver should keep away from the matte.
TRAINER_REFERENCE_FOREGROUND_ANCHORS: Final[tuple[brand.Color, ...]] = (
    brand.Color("#C0542A", "Trainer Red", "Canonical cap and vest accent from trainer.png"),
    brand.Color("#6E8FA8", "Trainer Denim", "Canonical jean fill from trainer.png"),
    brand.Color("#2A1E16", "Trainer Tee", "Dark undershirt fill"),
    brand.MUSTARD_YELLOW,
    *brand.SPRITE_CHROMA_PROTECTED_COLORS,
)

_TRAINER_DENIM = brand.Color("#6E8FA8", "Trainer Denim", "Likely pant fill")


def solve_trainer_reference_background(likeness_bytes: bytes) -> brand.Color:
    """Pick a chroma-key matte for a generated trainer reference sprite."""
    sampled = _sample_likeness_foreground_colors(likeness_bytes)
    skin = _sample_likeness_skin_colors(likeness_bytes)
    foreground = (*TRAINER_REFERENCE_FOREGROUND_ANCHORS, *sampled, *skin)
    return brand.solve_background_color(
        *foreground,
        hue_protected=(*sampled, *skin, brand.BURNT_ORANGE, _TRAINER_DENIM),
    )


def _sample_likeness_foreground_colors(likeness_bytes: bytes, *, max_colors: int = 5) -> tuple[brand.Color, ...]:
    """Extract a few dominant center-crop colors from the uploaded likeness photo."""
    with Image.open(io.BytesIO(likeness_bytes)) as image:
        rgb = np.asarray(_center_crop(image.convert("RGB")), dtype=np.uint8)

    buckets = (rgb // 32) * 32 + 16
    flat = buckets.reshape(-1, 3)
    unique, counts = np.unique(flat, axis=0, return_counts=True)
    ranked = sorted(zip(counts.tolist(), unique.tolist(), strict=True), reverse=True)

    colors: list[brand.Color] = []
    for _, channel in ranked:
        red, green, blue = (int(channel[0]), int(channel[1]), int(channel[2]))
        if not _is_useful_foreground_sample(red, green, blue):
            continue
        colors.append(
            brand.Color(
                f"#{red:02X}{green:02X}{blue:02X}",
                "Likeness sample",
                "Dominant color from uploaded photo",
            )
        )
        if len(colors) >= max_colors:
            break

    return tuple(colors)


def _sample_likeness_skin_colors(likeness_bytes: bytes, *, max_colors: int = 3) -> tuple[brand.Color, ...]:
    """Sample likely skin tones from the upper face region of the likeness photo."""
    with Image.open(io.BytesIO(likeness_bytes)) as image:
        width, height = image.size
        face = image.crop(
            (
                int(width * 0.25),
                int(height * 0.05),
                int(width * 0.75),
                max(int(height * 0.05) + 1, int(height * 0.45)),
            )
        ).convert("RGB")
        rgb = np.asarray(face, dtype=np.uint8)

    buckets = (rgb // 24) * 24 + 12
    flat = buckets.reshape(-1, 3)
    unique, counts = np.unique(flat, axis=0, return_counts=True)
    ranked = sorted(zip(counts.tolist(), unique.tolist(), strict=True), reverse=True)

    colors: list[brand.Color] = []
    for _, channel in ranked:
        red, green, blue = (int(channel[0]), int(channel[1]), int(channel[2]))
        if not _is_skin_tone_sample(red, green, blue):
            continue
        colors.append(
            brand.Color(
                f"#{red:02X}{green:02X}{blue:02X}",
                "Likeness skin",
                "Face-region skin tone from uploaded photo",
            )
        )
        if len(colors) >= max_colors:
            break

    return tuple(colors)


def _is_skin_tone_sample(red: int, green: int, blue: int) -> bool:
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    if luminance < 45 or luminance > 230:
        return False
    if red <= green or green < blue * 0.75:
        return False
    spread = max(red, green, blue) - min(red, green, blue)
    return spread > 6


def _center_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    left = int(width * 0.15)
    top = int(height * 0.05)
    right = max(left + 1, int(width * 0.85))
    bottom = max(top + 1, int(height * 0.95))
    return image.crop((left, top, right, bottom))


def _is_useful_foreground_sample(red: int, green: int, blue: int) -> bool:
    luminance = 0.299 * red + 0.587 * green + 0.114 * blue
    if luminance > 235 or luminance < 18:
        return False
    spread = max(red, green, blue) - min(red, green, blue)
    return spread > 8 or luminance < 200
