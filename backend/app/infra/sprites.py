"""
Monster sprite generation via Together AI FLUX.1-schnell.
Maps VibemonPayload → MonsterState → prompt → image.
Sprites cached to disk by UID.
"""
from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

import niquests
import structlog
from rembg import remove as rembg_remove
from together import AsyncTogether

from app.domain.models import VibemonPayload

log = structlog.get_logger(__name__)

SPRITES_DIR = Path(__file__).parent.parent.parent / "static" / "sprites"
DEFAULT_MODEL = "black-forest-labs/FLUX.1-schnell"


# ── Enums ─────────────────────────────────────────────────────────────────────

class EvolutionStage(Enum):
    BABY  = "Baby"
    MID   = "Mid"
    FINAL = "Final"

class BattleRole(Enum):
    TANK      = "Tank"
    SWEEPER   = "Sweeper"
    SUPPORT   = "Support"
    TRICKSTER = "Trickster"

class SizeClass(Enum):
    SMALL  = "Small"
    MEDIUM = "Medium"
    LARGE  = "Large"

class IdleStance(Enum):
    AGGRESSIVE = "Aggressive"
    DEFENSIVE  = "Defensive"
    PASSIVE    = "Passive"
    PLAYFUL    = "Playful"

class BattleContext(Enum):
    PLAYER = "Player"
    ENEMY  = "Enemy"

class BodyType(Enum):
    BIPEDAL   = "Bipedal"
    QUADRUPED = "Quadruped"
    AMORPHOUS = "Amorphous"
    WINGED    = "Winged"

class ExtraFeature(Enum):
    WINGS    = "Wings"
    HORNS    = "Horns"
    ANTENNAE = "Antennae"
    CARAPACE = "Carapace"
    FINS     = "Fins"

class SurfaceTexture(Enum):
    SOFT_FUR       = "Soft velvet fur"
    CERAMIC_PLATES = "Matte ceramic plating"
    CRYSTAL_SCALES = "Crystalline scales"
    MOLTEN_ROCK    = "Molten rock skin"
    LIQUID_GLASS   = "Liquid glass membrane"

class ElementalType(Enum):
    FIRE     = "Fire"
    WATER    = "Water"
    GRASS    = "Grass"
    ELECTRIC = "Electric"
    ICE      = "Ice"
    FIGHTING = "Fighting"
    POISON   = "Poison"
    GROUND   = "Ground"
    FLYING   = "Flying"
    PSYCHIC  = "Psychic"
    BUG      = "Bug"
    ROCK     = "Rock"
    GHOST    = "Ghost"
    DRAGON   = "Dragon"
    DARK     = "Dark"
    STEEL    = "Steel"
    FAIRY    = "Fairy"
    NORMAL   = "Normal"

class EffectIntensity(Enum):
    SUBTLE   = "Subtle"
    MODERATE = "Moderate"
    DRAMATIC = "Dramatic"


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ElementalEffect:
    description: str
    placement:   str
    intensity:   EffectIntensity

@dataclass
class ColorPalette:
    primary:   str
    secondary: str
    accent:    str

@dataclass
class MonsterState:
    evolution_stage:   EvolutionStage
    battle_role:       BattleRole
    size_class:        SizeClass
    idle_stance:       IdleStance
    battle_context:    BattleContext
    body_type:         BodyType
    limb_count:        int
    extra_features:    list[ExtraFeature]
    surface_texture:   SurfaceTexture
    signature_feature: str
    primary_type:      ElementalType
    secondary_type:    Optional[ElementalType]
    effect:            ElementalEffect
    palette:           ColorPalette
    name:              str = "monster"


# ── Static lookup tables ──────────────────────────────────────────────────────

STAGE_COMPLEXITY = {
    EvolutionStage.BABY:  "simple rounded shapes, large eyes, minimal details, 2-3 color palette, no intimidating features",
    EvolutionStage.MID:   "moderate detail, defined anatomy, 3-4 colors, one signature feature emerging",
    EvolutionStage.FINAL: "high detail, sharp ornate silhouette, full color palette, signature feature fully realized, optional aura",
}

STANCE_DESCRIPTION = {
    IdleStance.AGGRESSIVE: "weight forward, chest out, claws raised, slight forward lean, ready to strike",
    IdleStance.DEFENSIVE:  "hunched and coiled, limbs pulled close, eyes narrowed, guarded posture",
    IdleStance.PASSIVE:    "relaxed upright stance, weight centered, neutral expression, slight sway",
    IdleStance.PLAYFUL:    "off-balance lean, one limb raised casually, open expression, loose posture",
}

PERSPECTIVE_DESCRIPTION = {
    BattleContext.PLAYER: "back-facing, oriented right, facing away from viewer",
    BattleContext.ENEMY:  "front-facing, oriented left, weight shifted forward",
}

OUTLINE_WEIGHT = {
    EvolutionStage.BABY:  "thin 1px",
    EvolutionStage.MID:   "1px",
    EvolutionStage.FINAL: "bold 2px",
}

STATIC_RENDER = (
    "HD-2D high-fidelity pixel art, crisp pixel aesthetic, "
    "soft cel shading with ambient occlusion, "
    "dynamic rim lighting with secondary fill light, "
    "colored outlines matching local surface color with no harsh black edges, "
    "static idle pose mid-breath-cycle with slight weight shift, "
    "isolated on transparent background, "
    "single subject centered, no background, no ground, no shadow, no UI elements"
)

SIGNATURE_FEATURES: dict[str, str] = {
    "Fire":     "Cracked chest plate with molten magma glowing through the fissures",
    "Water":    "Crystalline water orb orbiting the body, rippling with each movement",
    "Grass":    "Flowering vines wrapping around the torso, blooming when calm",
    "Electric": "Crackling lightning corona surrounding the head and shoulders",
    "Ice":      "Frost-rimed armor plates growing from the spine in sharp geometric formations",
    "Fighting": "Knuckles wrapped in glowing energy wraps, pulsing with each breath",
    "Poison":   "Iridescent toxic sacs along the jaw, dripping luminescent venom",
    "Ground":   "Stone shoulder pauldrons with ancient runes etched into the surface",
    "Flying":   "Tail feathers that shimmer between solid and translucent with motion",
    "Psychic":  "Third eye on the forehead, iris spinning slowly with a soft violet glow",
    "Bug":      "Exoskeleton segments that shift and click when the creature moves",
    "Rock":     "Dense mineral growths erupting from the back like a natural crown",
    "Ghost":    "Translucent lower body fading into wispy ectoplasm trails",
    "Dragon":   "Iridescent scale ridge running crown to tail, refracting light",
    "Dark":     "Shadow cloak draping from the shoulders, absorbing surrounding light",
    "Steel":    "Mirror-polished chest plate engraved with circuit-like geometric patterns",
    "Fairy":    "Luminous wing-like membranes behind the ears, pastel and translucent",
    "Normal":   "Oversized expressive eyes that shift hue with the creature's mood",
}

ELEMENT_EFFECTS: dict[str, tuple[str, str, EffectIntensity]] = {
    "Fire":     ("Ember sparks and licks of flame drifting upward", "shoulders and tail", EffectIntensity.MODERATE),
    "Water":    ("Tiny water droplets beading and rolling off the surface", "surrounding body", EffectIntensity.SUBTLE),
    "Grass":    ("Drifting pollen spores and tiny leaf fragments", "around the torso", EffectIntensity.SUBTLE),
    "Electric": ("Crackling lightning arcs between raised spines", "along the back", EffectIntensity.DRAMATIC),
    "Ice":      ("Frost crystals forming and dissolving in the air", "surrounding extremities", EffectIntensity.MODERATE),
    "Fighting": ("Shockwave ripples emanating from fists", "around the limbs", EffectIntensity.MODERATE),
    "Poison":   ("Toxic miasma curling upward in slow spirals", "rising from the body", EffectIntensity.SUBTLE),
    "Ground":   ("Dust and pebbles floating in a slow orbit", "around the base", EffectIntensity.SUBTLE),
    "Flying":   ("Wind currents made visible as shimmering streaks", "trailing behind", EffectIntensity.MODERATE),
    "Psychic":  ("Softly glowing psychic runes orbiting the head", "around the head", EffectIntensity.DRAMATIC),
    "Bug":      ("Iridescent wing-dust scattering in tiny motes", "drifting off the wings", EffectIntensity.SUBTLE),
    "Rock":     ("Pebbles and stone chips crumbling and reforming", "around the body", EffectIntensity.MODERATE),
    "Ghost":    ("Wispy ectoplasm tendrils reaching outward", "extending from limbs", EffectIntensity.DRAMATIC),
    "Dragon":   ("Prismatic light refracting through scale ridges", "along the body", EffectIntensity.DRAMATIC),
    "Dark":     ("Shadow tendrils reaching and curling back", "around the edges", EffectIntensity.MODERATE),
    "Steel":    ("Metallic sparks and magnetic field shimmer", "around the chest", EffectIntensity.SUBTLE),
    "Fairy":    ("Soft sparkle motes and glowing petals drifting down", "falling around", EffectIntensity.MODERATE),
    "Normal":   ("Warm ambient glow pulsing gently", "surrounding the whole body", EffectIntensity.SUBTLE),
}


# ── VibemonPayload → MonsterState mapper ─────────────────────────────────────

def _hsl_color_name(h: float, s: float, l: float) -> str:
    if s < 0.25:
        if l < 0.3:
            return "charcoal grey"
        elif l < 0.6:
            return "slate grey"
        else:
            return "pearl white"
    prefix = "pale " if l > 0.70 else ("deep " if l < 0.35 else "")
    for threshold, name in [
        (15,  "red"),
        (35,  "orange"),
        (60,  "golden yellow"),
        (90,  "yellow-green"),
        (150, "green"),
        (175, "teal"),
        (210, "cyan"),
        (240, "sky blue"),
        (265, "blue"),
        (290, "indigo"),
        (320, "purple"),
        (345, "magenta"),
        (360, "red"),
    ]:
        if h <= threshold:
            return f"{prefix}{name}"
    return f"{prefix}red"


def vibemon_to_monster_state(payload: VibemonPayload, context: BattleContext) -> MonsterState:
    stats = payload.stats
    dna   = payload.visual_dna

    # Evolution stage from total BST
    total = (
        stats.hp + stats.attack + stats.defense
        + stats.sp_attack + stats.sp_defense + stats.speed
    )
    if total < 900:
        stage = EvolutionStage.BABY
    elif total < 1200:
        stage = EvolutionStage.MID
    else:
        stage = EvolutionStage.FINAL

    # Battle role from dominant stat
    dominant = max(
        {"hp": stats.hp, "defense": stats.defense, "attack": stats.attack,
         "speed": stats.speed, "sp_attack": stats.sp_attack, "sp_defense": stats.sp_defense},
        key=lambda k: {"hp": stats.hp, "defense": stats.defense, "attack": stats.attack,
                       "speed": stats.speed, "sp_attack": stats.sp_attack,
                       "sp_defense": stats.sp_defense}[k],
    )
    role = {
        "hp": BattleRole.TANK, "defense": BattleRole.TANK,
        "attack": BattleRole.SWEEPER, "speed": BattleRole.SWEEPER,
        "sp_attack": BattleRole.TRICKSTER, "sp_defense": BattleRole.SUPPORT,
    }[dominant]

    # Size from size_scale
    if dna.size_scale < 0.95:
        size = SizeClass.SMALL
    elif dna.size_scale < 1.15:
        size = SizeClass.MEDIUM
    else:
        size = SizeClass.LARGE

    # Idle stance
    if context == BattleContext.PLAYER:
        stance = IdleStance.AGGRESSIVE
    elif stats.defense > stats.attack:
        stance = IdleStance.DEFENSIVE
    else:
        stance = IdleStance.AGGRESSIVE

    # Body type from limb_style
    if dna.limb_count == 0:
        body_type = BodyType.AMORPHOUS
    elif dna.limb_style == "wing":
        body_type = BodyType.WINGED
    elif dna.limb_style == "elongated":
        body_type = BodyType.BIPEDAL
    else:
        body_type = BodyType.QUADRUPED

    # Extra features
    features: list[ExtraFeature] = []
    if dna.limb_style == "wing" and dna.limb_count > 0:
        features.append(ExtraFeature.WINGS)
    if dna.texture_pattern == "scales":
        features.append(ExtraFeature.CARAPACE)
    if dna.texture_pattern == "cracks":
        features.append(ExtraFeature.HORNS)
    if stats.sp_attack > 170:
        features.append(ExtraFeature.ANTENNAE)

    # Surface texture
    texture = {
        "dots":    SurfaceTexture.SOFT_FUR,
        "stripes": SurfaceTexture.CERAMIC_PLATES,
        "scales":  SurfaceTexture.CRYSTAL_SCALES,
        "cracks":  SurfaceTexture.MOLTEN_ROCK,
        "none":    SurfaceTexture.LIQUID_GLASS,
    }.get(dna.texture_pattern, SurfaceTexture.LIQUID_GLASS)

    # Elemental effect
    eff_desc, eff_place, eff_intensity = ELEMENT_EFFECTS.get(
        stats.element,
        ("Faint energy aura", "surrounding body", EffectIntensity.SUBTLE),
    )

    # Element types (graceful fallback to Normal)
    try:
        primary_type = ElementalType(stats.element)
    except ValueError:
        primary_type = ElementalType.NORMAL

    secondary_type: Optional[ElementalType] = None
    if stats.element_secondary:
        try:
            secondary_type = ElementalType(stats.element_secondary)
        except ValueError:
            pass

    # Sanitize uid for use as filename
    safe_name = payload.uid.replace("/", "_").replace("\\", "_").replace(":", "_")

    return MonsterState(
        evolution_stage=stage,
        battle_role=role,
        size_class=size,
        idle_stance=stance,
        battle_context=context,
        body_type=body_type,
        limb_count=dna.limb_count,
        extra_features=features,
        surface_texture=texture,
        signature_feature=SIGNATURE_FEATURES.get(
            stats.element, "Distinctive markings unique to this creature"
        ),
        primary_type=primary_type,
        secondary_type=secondary_type,
        effect=ElementalEffect(
            description=eff_desc,
            placement=eff_place,
            intensity=eff_intensity,
        ),
        palette=ColorPalette(
            primary=_hsl_color_name(*dna.color_primary),
            secondary=_hsl_color_name(*dna.color_secondary),
            accent=_hsl_color_name(*dna.color_accent),
        ),
        name=safe_name,
    )


# ── Prompt builder ────────────────────────────────────────────────────────────

def _generate_prompt(m: MonsterState) -> str:
    features = ", ".join(f.value for f in m.extra_features) if m.extra_features else "none"
    secondary = f"{m.secondary_type.value}/" if m.secondary_type else ""
    return (
        f"{secondary}{m.primary_type.value}-type {m.size_class.value.lower()} "
        f"{m.body_type.value.lower()} monster, {m.evolution_stage.value.lower()} evolution stage, "
        f"{STAGE_COMPLEXITY[m.evolution_stage]}, "
        f"{m.surface_texture.value.lower()}, "
        f"extra features: {features}, "
        f"signature feature: {m.signature_feature}, "
        f"color palette: {m.palette.primary} body, {m.palette.secondary} markings, {m.palette.accent} accents, "
        f"type effect: {m.effect.description}, {m.effect.placement.lower()}, {m.effect.intensity.value.lower()} intensity, "
        f"idle stance: {STANCE_DESCRIPTION[m.idle_stance]}, "
        f"perspective: {PERSPECTIVE_DESCRIPTION[m.battle_context]}, "
        f"{OUTLINE_WEIGHT[m.evolution_stage]} outlines, "
        f"{STATIC_RENDER}"
    )


# ── Together AI fetch ─────────────────────────────────────────────────────────

async def _fetch_image(prompt: str, api_key: str, model: str) -> bytes:
    client = AsyncTogether(api_key=api_key)
    response = await client.images.generate(
        prompt=prompt,
        model=model,
        width=512,
        height=512,
        steps=4,
        n=1,
    )
    item = response.data[0]

    # SDK may return b64_json or a URL depending on the model tier
    if item.b64_json:
        return base64.b64decode(item.b64_json)

    async with niquests.AsyncSession() as session:
        img_resp = await session.get(item.url)
        img_resp.raise_for_status()
        return img_resp.content


# ── Public API ────────────────────────────────────────────────────────────────

async def ensure_sprite(
    payload: VibemonPayload,
    context: BattleContext,
    model: str = DEFAULT_MODEL,
) -> Optional[str]:
    """
    Return URL path for a vibemon sprite, generating it if not cached.
    Returns None when TOGETHER_API_KEY is unset or generation fails.
    URL is relative to the backend root: /static/sprites/{safe_uid}.png
    """
    api_key = os.environ.get("TOGETHER_API_KEY", "")
    if not api_key:
        log.debug("sprite_skip_no_api_key", uid=payload.uid)
        return None

    safe_uid = payload.uid.replace("/", "_").replace("\\", "_").replace(":", "_")
    # Include context in the filename so player/enemy get different perspectives
    filename = f"{safe_uid}_{context.value.lower()}.png"
    sprite_path = SPRITES_DIR / filename

    if sprite_path.exists():
        log.info("sprite_cache_hit", uid=payload.uid, context=context.value)
        return f"/static/sprites/{filename}"

    monster = vibemon_to_monster_state(payload, context)
    prompt  = _generate_prompt(monster)

    try:
        image_bytes = await _fetch_image(prompt, api_key, model)
        image_bytes = await asyncio.to_thread(rembg_remove, image_bytes)
        SPRITES_DIR.mkdir(parents=True, exist_ok=True)
        sprite_path.write_bytes(image_bytes)
        log.info("sprite_generated", uid=payload.uid, context=context.value, bytes=len(image_bytes))
        return f"/static/sprites/{filename}"
    except Exception:
        log.exception("sprite_generation_failed", uid=payload.uid, context=context.value)
        return None
