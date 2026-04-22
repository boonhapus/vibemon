"""Visual DNA assembly for sprite prompts.

Pure builder functions + a thin ``VisualDNA`` attrs object that knows how to render
itself against ``vibemon-sprites.mdc``. Keep the template dumb: each prompt section
is a single string built here.
"""

from collections.abc import Iterable
import pathlib
import re

import attrs
import jinja2

from app import schema, types


DEFAULT_SPRITE_TEMPLATE = "vibemon-sprites.mdc"

_RE_MARKDOWN_FRONTMATTER = re.compile(r"^---\n.*?\n---\n\n?", re.DOTALL)

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


# ── Static lexicons ──────────────────────────────────────────────────────────────────

ELEMENT_LEXICON: dict[types.VibemonTypeT, str] = {
    types.VibemonTypeT.NORMAL: "earth tones, neutral palette, mammalian or avian silhouette",
    types.VibemonTypeT.FIRE: "warm reds and oranges, ember glow, smouldering surfaces",
    types.VibemonTypeT.WATER: "cool blues, translucent or wet materials, droplet motifs",
    types.VibemonTypeT.ELECTRIC: "vivid yellow highlights, crackling filaments, angular bolts",
    types.VibemonTypeT.GRASS: "verdant greens, leaf textures, organic curves and vines",
    types.VibemonTypeT.ICE: "pale cyan, frosted surfaces, crystalline facets",
    types.VibemonTypeT.FIGHTING: "muscular build, bandaged or armoured fists, combat stance",
    types.VibemonTypeT.POISON: "sickly purples, dripping textures, faint vapour wisps",
    types.VibemonTypeT.GROUND: "tans and browns, rocky textures, burrowing features",
    types.VibemonTypeT.FLYING: "winged silhouette, feathered or membrane details, streamlined form",
    types.VibemonTypeT.PSYCHIC: "pastel magenta, geometric halos, introspective gaze",
    types.VibemonTypeT.BUG: "chitinous segments, compound eyes, antennae",
    types.VibemonTypeT.ROCK: "mineral plating, jagged outcrops, weathered grey",
    types.VibemonTypeT.GHOST: "translucent body, wisping edges, spectral aura",
    types.VibemonTypeT.DRAGON: "regal scales, horned crest, imposing stature",
    types.VibemonTypeT.DARK: "deep charcoals, glowing eyes, shadowed silhouette",
    types.VibemonTypeT.STEEL: "metallic sheen, rivets or plating, cold reflective finish",
    types.VibemonTypeT.FAIRY: "soft pinks and whites, sparkling particles, delicate features",
}


# ── Builders (pure) ──────────────────────────────────────────────────────────────────

_BST_TIERS: tuple[tuple[int, str], ...] = (
    (350, "fragile rookie"),
    (450, "modest adolescent"),
    (520, "balanced midgame"),
    (600, "powerful pseudo-legendary"),
    (10_000, "legendary"),
)

_LEAN_THRESHOLD = 20
_TEMPO_THRESHOLD = 15


def _bst_tier(bst: int) -> str:
    for cap, label in _BST_TIERS:
        if bst <= cap:
            return label
    return _BST_TIERS[-1][1]


def stat_signature(mon: "schema.Vibemon") -> str:
    """Deterministic prose describing BST tier, dominant stats, and role lean."""
    bst = mon.bst
    tier = _bst_tier(bst)

    stats: dict[str, int] = {
        "HP": mon.base_hp,
        "Atk": mon.base_attack,
        "Def": mon.base_defense,
        "SpA": mon.base_sp_attack,
        "SpD": mon.base_sp_defense,
        "Spe": mon.base_speed,
    }
    top_two = sorted(stats.items(), key=lambda kv: kv[1], reverse=True)[:2]
    top_desc = ", ".join(f"{name} {value}" for name, value in top_two)

    offence_diff = mon.base_attack - mon.base_sp_attack
    if offence_diff > _LEAN_THRESHOLD:
        lean = "physical"
    elif -offence_diff > _LEAN_THRESHOLD:
        lean = "special"
    else:
        lean = "mixed"

    bulk = (mon.base_hp + mon.base_defense + mon.base_sp_defense) / 3
    if mon.base_speed - bulk > _TEMPO_THRESHOLD:
        tempo = "swift"
    elif bulk - mon.base_speed > _TEMPO_THRESHOLD:
        tempo = "bulky"
    else:
        tempo = "balanced"

    return f"{tier}; {lean} offence, {tempo} build; dominant {top_desc} (BST {bst})"


def element_visuals(elements: Iterable[types.VibemonTypeT]) -> str:
    """One lexicon line per element. Dual-type interaction is deferred to the LLM."""
    unique = list(dict.fromkeys(elements))  # preserve order, drop dupes
    if not unique:
        unique = [types.VibemonTypeT.NORMAL]
    return "\n".join(f"- {element.value}: {ELEMENT_LEXICON[element]}" for element in unique)


def trainer_steering(description: str, *, max_chars: int = 500) -> str:
    """Normalize whitespace and cap length on user-authored flavor."""
    normalized = " ".join(description.split()).strip()
    if len(normalized) > max_chars:
        normalized = normalized[: max_chars - 1].rstrip() + "…"
    return normalized


def provider_echo(signatures: Iterable["schema.AffinitySignature"]) -> str:
    """Bulleted per-provider visual echo, sorted by intensity descending."""
    ordered = sorted(signatures, key=lambda s: s.intensity, reverse=True)
    if not ordered:
        return "- (no provider contributions recorded)"

    lines: list[str] = []
    for signature in ordered:
        parts: list[str] = [f"{signature.provider_id} @ {signature.intensity:.2f}"]
        if signature.visual_notes:
            parts.append(signature.visual_notes)
        if signature.elements:
            parts.append(", ".join(element.value for element in signature.elements))
        lines.append("- " + " — ".join(parts))
    return "\n".join(lines)


# ── VisualDNA ────────────────────────────────────────────────────────────────────────


@attrs.frozen
class VisualDNA:
    """Prompt payload for the sprite template.

    All fields are pre-rendered strings; the template only substitutes, never formats.
    """

    name: str
    stat_signature: str
    element_visuals: str
    trainer_steering: str
    provider_echo: str
    bg_hex: str = "#C47A7A"

    def render(self, template: str = DEFAULT_SPRITE_TEMPLATE) -> str:
        raw = _env.get_template(template).render(visual=self)
        return _RE_MARKDOWN_FRONTMATTER.sub("", raw)


def build_visual_dna(mon: "schema.Vibemon") -> VisualDNA:
    return VisualDNA(
        name=mon.name,
        stat_signature=stat_signature(mon),
        element_visuals=element_visuals(mon.elements),
        trainer_steering=trainer_steering(mon.description),
        provider_echo=provider_echo(mon.birth_affinities),
    )
