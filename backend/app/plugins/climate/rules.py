"""
Weather ruleset.

Maps the canonical weather channels (produced by any weather provider)
and weather event categories to Vibemon elements, stats, and visual notes.

Pure data. No imports from any specific provider.
"""
from app.plugins.engine import ElementRule, Ruleset
from app import types
from . import moves


# ── Element rules ─────────────────────────────────────────────────────────
#
# Each rule: element scores when channel value (post-inversion) clears
# the floor. Floors are the only knob — they set where each element
# starts to activate on the [0, 1] global range.

_ELEMENT_RULES: tuple[ElementRule, ...] = (
    # Thermal
    ElementRule(types.VibemonTypeT.FIRE,     "temperature", floor=0.40),
    ElementRule(types.VibemonTypeT.ICE,      "temperature", floor=0.30, invert=True),

    # Moisture
    ElementRule(types.VibemonTypeT.WATER,    "rain",        floor=0.00),
    ElementRule(types.VibemonTypeT.ICE,      "snow",        floor=0.00),
    ElementRule(types.VibemonTypeT.GRASS,    "dew_point",   floor=0.30),
    ElementRule(types.VibemonTypeT.GROUND,   "dew_point",   floor=0.30, invert=True),
    ElementRule(types.VibemonTypeT.POISON,   "humidity",    floor=0.60),

    # Kinetic
    ElementRule(types.VibemonTypeT.FLYING,   "wind_speed",  floor=0.20),

    # Solar
    ElementRule(types.VibemonTypeT.ELECTRIC, "uv_index",    floor=0.30),

    # Terrain
    ElementRule(types.VibemonTypeT.ROCK,     "elevation",   floor=0.25),
    ElementRule(types.VibemonTypeT.GROUND,   "elevation",   floor=0.00),

    # Atmospheric
    ElementRule(types.VibemonTypeT.GHOST,    "visibility",  floor=0.40, invert=True),
    ElementRule(types.VibemonTypeT.DARK,     "visibility",  floor=0.75, invert=True),
)


# ── Severity scale ────────────────────────────────────────────────────────
#
# Index → bonus multiplier. Indexed by Event.severity.
#   0 = NONE      no bonus
#   1 = LIGHT     ambient conditions
#   2 = MODERATE  notable weather event
#   3 = HEAVY     dominant weather event

_SEVERITY_SCALE: tuple[float, ...] = (0.00, 0.15, 0.30, 0.45)


# ── Event affinities ──────────────────────────────────────────────────────
#
# category → ((element, weight), ...). Final bonus per element =
# weight * severity_scale[event.severity]. A weight of 1.0 paired with
# HEAVY severity yields a 0.45 contribution.

_EVENT_AFFINITIES: dict[str, tuple[tuple[types.VibemonTypeT, float], ...]] = {
    "clear":            ((types.VibemonTypeT.FIRE,     1.0),),
    "cloudy":           ((types.VibemonTypeT.NORMAL,   1.0),),
    "fog":              ((types.VibemonTypeT.GHOST,    1.0),),
    "drizzle":          ((types.VibemonTypeT.WATER,    1.0),),
    "freezing_drizzle": ((types.VibemonTypeT.ICE,      1.0), (types.VibemonTypeT.WATER, 0.5)),
    "rain":             ((types.VibemonTypeT.WATER,    1.0),),
    "freezing_rain":    ((types.VibemonTypeT.ICE,      1.0), (types.VibemonTypeT.WATER, 0.5)),
    "rain_showers":     ((types.VibemonTypeT.WATER,    1.0),),
    "snow":             ((types.VibemonTypeT.ICE,      1.0),),
    "snow_grains":      ((types.VibemonTypeT.ICE,      0.5),),
    "rain_with_snow":   ((types.VibemonTypeT.ICE,      1.0), (types.VibemonTypeT.WATER, 0.5)),
    "hail":             ((types.VibemonTypeT.ICE,      1.0), (types.VibemonTypeT.ROCK,  0.5)),
    "thunderstorm":     ((types.VibemonTypeT.ELECTRIC, 1.0),),
    "dust_storm":       ((types.VibemonTypeT.GROUND,   1.0),),
}


# ── Stat map ──────────────────────────────────────────────────────────────

_STAT_MAP: dict[str, str] = {
    "base_hp":         "temp_spread",
    "base_attack":     "wind_gusts",
    "base_defense":    "elevation",
    "base_sp_attack":  "radiation",
    "base_sp_defense": "humidity",
    "base_speed":      "wind_speed",
}


# ── Visual notes ──────────────────────────────────────────────────────────

_VISUAL_NOTES: dict[str, str] = {
    "clear":            "Clear, high-contrast form with sharp edge-geometry.",
    "cloudy":           "Semi-translucent with soft internal refraction.",
    "fog":              "Diffuse, low-opacity silhouette shrouded in mist.",
    "drizzle":          "Glistening exterior with constant particle-drip effects.",
    "freezing_drizzle": "Glassy ice veneer forming over a drip-textured surface.",
    "rain":             "Streaming liquid channels carved across the form.",
    "freezing_rain":    "Smooth ice casing with trapped liquid veins beneath.",
    "rain_showers":     "Burst-pattern splash rings radiating outward on impact.",
    "snow":             "Frosted crystalline armor with soft powder layering.",
    "snow_grains":      "Micro-crystal shimmer suspended around the silhouette.",
    "rain_with_snow":   "Slushy cascade mixing rain streaks with snow clumps.",
    "hail":             "Pitted ice-stone exterior, jagged where impacts have landed.",
    "thunderstorm":     "Volatile storm-wracked form with lightning-threaded contours.",
    "dust_storm":       "Granular, wind-scoured silhouette wreathed in airborne grit.",
}

_DEFAULT_NOTE = "Neutral, undefined form."


_MOVE_BY_NAME = {m.name: m for m in moves.MOVES}

_SIGNAL_MOVE_RULES = {
    "temperature": (
        (_MOVE_BY_NAME["Heat Index Surge"], 1.0),
        (_MOVE_BY_NAME["Scorching High"], 0.8),
        (_MOVE_BY_NAME["Sunstroke Beam"], 0.7),
        (_MOVE_BY_NAME["Black Ice Shard"], 1.0),
        (_MOVE_BY_NAME["Rime Needle"], 0.9),
    ),
    "temp_spread": (
        (_MOVE_BY_NAME["Polar Vortex Clamp"], 1.0),
        (_MOVE_BY_NAME["Heat Index Surge"], 0.6),
        (_MOVE_BY_NAME["Monsoon Spiral"], 0.5),
    ),
    "rain": (
        (_MOVE_BY_NAME["Sheet Rain"], 1.0),
        (_MOVE_BY_NAME["Downpour Driver"], 0.9),
        (_MOVE_BY_NAME["Drizzle Needle"], 0.8),
        (_MOVE_BY_NAME["Monsoon Spiral"], 0.7),
    ),
    "snow": (
        (_MOVE_BY_NAME["Hail Core Pelting"], 1.0),
        (_MOVE_BY_NAME["Flash Freeze"], 0.9),
        (_MOVE_BY_NAME["Black Ice Shard"], 0.8),
    ),
    "humidity": (
        (_MOVE_BY_NAME["Dew Point Bloom"], 0.8),
        (_MOVE_BY_NAME["Muggy Spore Drift"], 0.7),
        (_MOVE_BY_NAME["Humid Root Grasp"], 0.8),
    ),
    "dew_point": (
        (_MOVE_BY_NAME["Dew Point Bloom"], 1.0),
        (_MOVE_BY_NAME["Canopy Whip"], 0.8),
        (_MOVE_BY_NAME["Saturated Soil Hook"], 0.6),
    ),
    "wind_speed": (
        (_MOVE_BY_NAME["Gust Front"], 1.0),
        (_MOVE_BY_NAME["Crosswind Cut"], 0.9),
        (_MOVE_BY_NAME["Anemometer Spin"], 0.7),
    ),
    "wind_gusts": (
        (_MOVE_BY_NAME["Downdraft Slam"], 1.0),
        (_MOVE_BY_NAME["Jet Stream Shear"], 0.9),
        (_MOVE_BY_NAME["Cloud-to-Ground Bolt"], 0.6),
    ),
    "uv_index": (
        (_MOVE_BY_NAME["UV Microflare"], 1.0),
        (_MOVE_BY_NAME["Sunstroke Beam"], 0.8),
        (_MOVE_BY_NAME["Sheet Lightning Glow"], 0.5),
    ),
    "radiation": (
        (_MOVE_BY_NAME["Thermal Shimmer Lash"], 0.9),
        (_MOVE_BY_NAME["UV Microflare"], 0.8),
        (_MOVE_BY_NAME["Static Hair Snap"], 0.5),
    ),
    "elevation": (
        (_MOVE_BY_NAME["Crag Silhouette"], 1.0),
        (_MOVE_BY_NAME["Boulder Outcrop"], 0.9),
        (_MOVE_BY_NAME["Contour Line Burrow"], 0.7),
    ),
    "visibility": (
        (_MOVE_BY_NAME["Fog Echo"], 1.0),
        (_MOVE_BY_NAME["Vapor Wisp"], 0.9),
        (_MOVE_BY_NAME["Visibility Zero Trench"], 0.8),
        (_MOVE_BY_NAME["Curfew Veil"], 0.6),
    ),
}

_EVENT_MOVE_RULES = {
    "clear": (
        (_MOVE_BY_NAME["Fair Skies Nod"], 1.0),
        (_MOVE_BY_NAME["Isobaric Calm"], 0.8),
        (_MOVE_BY_NAME["Scorching High"], 0.5),
    ),
    "cloudy": (
        (_MOVE_BY_NAME["Partly Cloudy Glance"], 1.0),
        (_MOVE_BY_NAME["Station Model Shrug"], 0.8),
    ),
    "fog": (
        (_MOVE_BY_NAME["Fog Echo"], 1.0),
        (_MOVE_BY_NAME["Vapor Wisp"], 0.9),
        (_MOVE_BY_NAME["Deck Fog Roll"], 0.8),
    ),
    "drizzle": (
        (_MOVE_BY_NAME["Drizzle Needle"], 1.0),
        (_MOVE_BY_NAME["Sheet Rain"], 0.8),
    ),
    "freezing_drizzle": (
        (_MOVE_BY_NAME["Flash Freeze"], 1.0),
        (_MOVE_BY_NAME["Black Ice Shard"], 0.8),
    ),
    "rain": (
        (_MOVE_BY_NAME["Downpour Driver"], 1.0),
        (_MOVE_BY_NAME["Sheet Rain"], 0.9),
    ),
    "freezing_rain": (
        (_MOVE_BY_NAME["Hail Core Pelting"], 1.0),
        (_MOVE_BY_NAME["Flash Freeze"], 0.9),
    ),
    "rain_showers": (
        (_MOVE_BY_NAME["Monsoon Spiral"], 0.9),
        (_MOVE_BY_NAME["Sheet Rain"], 0.8),
    ),
    "snow": (
        (_MOVE_BY_NAME["Polar Vortex Clamp"], 1.0),
        (_MOVE_BY_NAME["Rime Needle"], 0.9),
    ),
    "snow_grains": (
        (_MOVE_BY_NAME["Rime Needle"], 0.9),
        (_MOVE_BY_NAME["Hail Core Pelting"], 0.7),
    ),
    "rain_with_snow": (
        (_MOVE_BY_NAME["Hail Core Pelting"], 1.0),
        (_MOVE_BY_NAME["Downpour Driver"], 0.9),
    ),
    "hail": (
        (_MOVE_BY_NAME["Hail Core Pelting"], 1.0),
        (_MOVE_BY_NAME["Landslip Hammer"], 0.5),
    ),
    "thunderstorm": (
        (_MOVE_BY_NAME["Thunderhead Core"], 1.0),
        (_MOVE_BY_NAME["Cloud-to-Ground Bolt"], 0.9),
        (_MOVE_BY_NAME["Ionized Gust"], 0.7),
    ),
    "dust_storm": (
        (_MOVE_BY_NAME["Isobar Stamp"], 1.0),
        (_MOVE_BY_NAME["Saturated Soil Hook"], 0.8),
        (_MOVE_BY_NAME["Landslip Hammer"], 0.6),
    ),
}


# ── Assembled ruleset ─────────────────────────────────────────────────────

WEATHER_RULESET = Ruleset(
    element_rules=_ELEMENT_RULES,
    event_affinities=_EVENT_AFFINITIES,
    severity_scale=_SEVERITY_SCALE,
    stat_map=_STAT_MAP,
    visual_notes=_VISUAL_NOTES,
    default_note=_DEFAULT_NOTE,
    signal_move_rules=_SIGNAL_MOVE_RULES,
    event_move_rules=_EVENT_MOVE_RULES,
    move_pool_size=10,
    primary_min=0.20,
    secondary_ratio=0.75,
)