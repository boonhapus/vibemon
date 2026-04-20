from __future__ import annotations

import json

import cattrs
from google import genai

from app.plugins.protocol import (
    Context,
    DataProvider,
    Delta,
    VisualDelta,
    STAT_NAMES,
    merge_deltas,
)
from app.schema import Vibemon
from app.sprite import Creature

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client

CREATURE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "anatomy": {
            "type": "object",
            "properties": {
                "head": {"type": "string"},
                "torso": {"type": "string"},
                "abdomen": {"type": "string"},
                "tail": {"type": "string"},
                "wings": {"type": "string"},
                "limbs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "count": {"type": "integer"},
                            "function": {"type": "string"},
                            "dominant": {"type": "boolean"},
                            "joint_count": {"type": "integer"},
                            "tip_detail": {"type": "string"},
                        },
                        "required": ["count", "function"],
                    },
                },
            },
            "required": ["limbs"],
        },
        "colors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "region": {"type": "string"},
                    "description": {"type": "string"},
                    "hex": {"type": "string"},
                },
                "required": ["region", "description", "hex"],
            },
        },
        "glow_rule": {"type": "string"},
    },
    "required": ["name", "anatomy", "colors", "glow_rule"],
}


def _build_creature_prompt(
    name: str,
    description: str,
    stats: dict[str, int],
    visual_hints: VisualDelta,
) -> str:
    lines = [
        f"Design a creature called '{name}' for a monster-battling game.",
        f"Description: {description}",
        "",
        "Stats (0-255 scale, higher = more pronounced trait):",
    ]
    for stat, value in stats.items():
        lines.append(f"  {stat}: {value}")

    lines.append("")
    lines.append("Use stats to inform physicality:")
    lines.append("  - High attack → muscular, heavy limbs, imposing build")
    lines.append("  - High sp_attack → ethereal features, glowing elements, arcane motifs")
    lines.append("  - High defense → armored, thick hide, compact frame")
    lines.append("  - High sp_defense → flowing/layered forms, wards, shimmering surfaces")
    lines.append("  - High speed → sleek, aerodynamic, long limbs, minimal bulk")
    lines.append("  - High max_hp → large body mass, robust proportions")

    if visual_hints.color_shifts:
        lines.append("")
        lines.append("Color hints from environment:")
        for region, shift in visual_hints.color_shifts.items():
            parts = [f"  {region}:"]
            if shift.hex_override:
                parts.append(f"use {shift.hex_override}")
            else:
                if shift.hue_rotation:
                    parts.append(f"hue shift {shift.hue_rotation:+.1f}°")
                if shift.lightness_adjust:
                    parts.append(f"lightness {shift.lightness_adjust:+.2f}")
            lines.append(" ".join(parts))

    if visual_hints.glow_rule_override:
        lines.append(f"Glow behavior: {visual_hints.glow_rule_override}")

    lines.append("")
    lines.append("Return a JSON creature with anatomy, colors (3-5 zones with hex), and a glow_rule.")
    return "\n".join(lines)


async def generate_creature(
    name: str,
    description: str,
    stats: dict[str, int],
    visual_hints: VisualDelta,
) -> Creature:
    prompt = _build_creature_prompt(name, description, stats, visual_hints)
    response = await _get_client().aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CREATURE_SCHEMA,
        ),
    )
    raw = json.loads(response.text)
    return cattrs.structure(raw, Creature)


async def birth_vibemon(
    name: str,
    user_description: str,
    context: Context,
    providers: list[DataProvider],
) -> Vibemon:
    deltas: list[tuple[float, Delta]] = []

    for provider in providers:
        if provider.name not in context.enabled_providers:
            continue
        intensity = await provider.intensity(context)
        delta = await provider.contribute(context)
        deltas.append((intensity, delta))

    base_stats = {stat: 0 for stat in STAT_NAMES}
    final_stats, merged_visual, desc_fragments = merge_deltas(base_stats, deltas)

    full_description = user_description
    if desc_fragments:
        full_description += "\n" + "\n".join(desc_fragments)

    creature = await generate_creature(name, full_description, final_stats, merged_visual)

    return Vibemon(
        name=name,
        description=full_description,
        creature=creature,
        base_hp=final_stats["max_hp"],
        base_attack=final_stats["attack"],
        base_defense=final_stats["defense"],
        base_sp_attack=final_stats["sp_attack"],
        base_sp_defense=final_stats["sp_defense"],
        base_speed=final_stats["speed"],
    )
