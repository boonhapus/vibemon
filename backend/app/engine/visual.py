from __future__ import annotations

import random
from typing import Tuple

from app.engine.models import VisualDNA, VibemonStats
from app.providers.base import SourceData

ELEMENT_BASE_HUES = {
    "Fire": 20.0,
    "Water": 210.0,
    "Ice": 190.0,
    "Electric": 55.0,
    "Grass": 115.0,
    "Ground": 32.0,
    "Dark": 275.0,
    "Psychic": 315.0,
    "Normal": 35.0,
}

ELEMENT_EYE_SHAPES = {
    "Fire": "diamond",
    "Water": "circle",
    "Ice": "slit",
    "Electric": "compound",
    "Grass": "circle",
    "Ground": "slit",
    "Dark": "slit",
    "Psychic": "diamond",
    "Normal": "circle",
}


def generate_palette(
    merged: SourceData,
    stats: VibemonStats,
    rng: random.Random,
) -> Tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    base_hue = merged.hue_primary
    if base_hue is None:
        base_hue = ELEMENT_BASE_HUES.get(stats.element, ELEMENT_BASE_HUES["Normal"])
    base_hue = (base_hue + rng.uniform(-15, 15)) % 360.0

    sat = 0.50 + (stats.sp_attack / 255.0) * 0.40
    lum = merged.luminosity if merged.luminosity is not None else 0.55

    h_secondary = (base_hue + 30.0 + rng.uniform(-10, 10)) % 360.0
    h_accent = (base_hue + 180.0 + rng.uniform(-20, 20)) % 360.0

    return (
        (base_hue, sat, lum),
        (h_secondary, sat * 0.85, min(lum * 1.05, 1.0)),
        (h_accent, min(sat * 1.2, 1.0), lum * 0.90),
        (h_accent, 0.90, 0.70),
    )


def generate_visual_dna(merged: SourceData, stats: VibemonStats, seed: int) -> VisualDNA:
    rng = random.Random(seed)

    n_points = 8 + int((stats.speed / 255.0) * 4)
    n_points = max(8, min(12, n_points))

    spikiness = 0.1 + (stats.attack / 255.0) * 0.5
    spikiness = max(0.0, min(0.6, spikiness))

    if stats.hp < 85:
        limb_count = 0
    elif stats.hp <= 170:
        limb_count = 1
    else:
        limb_count = 2

    if stats.speed > stats.defense:
        limb_style = "wing" if rng.random() < 0.5 else "elongated"
    else:
        limb_style = "stubby"

    eye_count = 1 if stats.sp_attack > 170 else 2
    eye_size = 0.04 + (stats.sp_defense / 255.0) * 0.08
    eye_size = max(0.04, min(0.12, eye_size))

    eye_shape = ELEMENT_EYE_SHAPES.get(stats.element, "circle")

    if stats.attack < 85:
        mouth_style = "none"
    elif stats.attack < 170:
        mouth_style = "line"
    elif stats.attack < 220:
        mouth_style = "open"
    else:
        mouth_style = "fanged"

    if stats.defense < 85:
        texture_pattern = "none"
    elif stats.defense < 140:
        texture_pattern = "dots"
    elif stats.defense < 190:
        texture_pattern = "stripes"
    elif stats.defense < 220:
        texture_pattern = "scales"
    else:
        texture_pattern = "cracks"

    outline_weight = 0.5 + (stats.defense / 255.0) * 3.0
    outline_weight = max(0.5, min(3.5, outline_weight))

    glow_intensity = stats.sp_attack / 255.0
    glow_intensity = max(0.0, min(1.0, glow_intensity))

    size_scale = 0.8 + (stats.hp / 255.0) * 0.5
    size_scale = max(0.8, min(1.3, size_scale))

    animation_speed = 0.5 + (stats.speed / 255.0) * 1.5
    animation_speed = max(0.5, min(2.0, animation_speed))

    cp, cs, ca, ce = generate_palette(merged, stats, rng)

    return VisualDNA(
        n_points=n_points,
        spikiness=spikiness,
        limb_count=limb_count,
        limb_style=limb_style,
        eye_count=eye_count,
        eye_size=eye_size,
        eye_shape=eye_shape,
        mouth_style=mouth_style,
        texture_pattern=texture_pattern,
        color_primary=cp,
        color_secondary=cs,
        color_accent=ca,
        color_eye=ce,
        outline_weight=outline_weight,
        glow_intensity=glow_intensity,
        size_scale=size_scale,
        animation_speed=animation_speed,
    )
