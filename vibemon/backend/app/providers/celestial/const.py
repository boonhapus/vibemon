"""Celestial provider constants: zodiac, dignity, scoring tables, and visual cues."""

from typing import Final, Literal

from app.domains.generation import types as generation_types
from app.domains.move.types import VibemonTypeT

type MoonBucketT = Literal["full", "new", "waxing_crescent", "waxing_gibbous", "waning_gibbous", "waning_crescent"]
type SeasonArcT = Literal["midsummer", "midwinter"]

ZODIAC_SIGNS: Final[tuple[str, ...]] = (
    "aries",
    "taurus",
    "gemini",
    "cancer",
    "leo",
    "virgo",
    "libra",
    "scorpio",
    "sagittarius",
    "capricorn",
    "aquarius",
    "pisces",
)

FIRE_SIGNS: Final[frozenset[str]] = frozenset({"aries", "leo", "sagittarius"})
EARTH_SIGNS: Final[frozenset[str]] = frozenset({"taurus", "virgo", "capricorn"})
AIR_SIGNS: Final[frozenset[str]] = frozenset({"gemini", "libra", "aquarius"})
WATER_SIGNS: Final[frozenset[str]] = frozenset({"cancer", "scorpio", "pisces"})

SIGN_ELEMENT: Final[dict[str, VibemonTypeT]] = (
    dict.fromkeys(FIRE_SIGNS, VibemonTypeT.FIRE)
    | dict.fromkeys(EARTH_SIGNS, VibemonTypeT.ROCK)
    | dict.fromkeys(AIR_SIGNS, VibemonTypeT.FLYING)
    | dict.fromkeys(WATER_SIGNS, VibemonTypeT.WATER)
)

CHART_POINT_WEIGHTS: Final[dict[str, float]] = {
    "sun": 1.0,
    "moon": 0.75,
    "ascendant": 0.5,
}

STELLIUM_SIGN_COUNT: Final[int] = 3
STELLIUM_ELEMENT_BOOST: Final[float] = 1.25

DOMICILE: Final[dict[str, frozenset[str]]] = {
    "sun": frozenset({"leo"}),
    "moon": frozenset({"cancer"}),
    "mercury": frozenset({"gemini", "virgo"}),
    "venus": frozenset({"taurus", "libra"}),
    "mars": frozenset({"aries", "scorpio"}),
    "jupiter": frozenset({"sagittarius", "pisces"}),
    "saturn": frozenset({"capricorn", "aquarius"}),
}

EXALTATION: Final[dict[str, str]] = {
    "sun": "aries",
    "moon": "taurus",
    "mercury": "virgo",
    "venus": "pisces",
    "mars": "capricorn",
    "jupiter": "cancer",
    "saturn": "libra",
}

SOLAR_PHASE_ELEMENTS: Final[dict[generation_types.SolarPhase, tuple[tuple[VibemonTypeT, float], ...]]] = {
    generation_types.SolarPhase.DAWN: ((VibemonTypeT.FAIRY, 0.42), (VibemonTypeT.PSYCHIC, 0.38)),
    generation_types.SolarPhase.DAY: ((VibemonTypeT.ELECTRIC, 0.40), (VibemonTypeT.FLYING, 0.35)),
    generation_types.SolarPhase.DUSK: ((VibemonTypeT.GHOST, 0.42), (VibemonTypeT.FAIRY, 0.38)),
    generation_types.SolarPhase.NIGHT: ((VibemonTypeT.DARK, 0.40), (VibemonTypeT.GHOST, 0.35)),
}

ANGULAR_HOUSES: Final[frozenset[int]] = frozenset({1, 4, 7, 10})

# Angular houses (1/4/7/10) dominate, succedent (2/5/8/11) follow, cadent (3/6/9/12) trail.
HOUSE_WEIGHT: Final[dict[int, float]] = (
    dict.fromkeys(ANGULAR_HOUSES, 1.0) | dict.fromkeys((2, 5, 8, 11), 0.65) | dict.fromkeys((3, 6, 9, 12), 0.35)
)

TRADITIONAL_BODIES: Final[tuple[str, ...]] = (
    "sun",
    "moon",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
)

VISIBLE_PLANETS: Final[tuple[str, ...]] = ("mercury", "venus", "mars", "jupiter", "saturn")

ECLIPSE_ELEMENT_BOOST: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.PSYCHIC, 0.12),
    (VibemonTypeT.DARK, 0.10),
)

# Moon-illumination bands: above/below these the moon reads as full/new
# instead of waxing or waning. Also drive the full/new phrasing in visual notes.
FULL_MOON_MIN_ILLUMINATION: Final[float] = 0.85
NEW_MOON_MAX_ILLUMINATION: Final[float] = 0.15

FULL_MOON_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.PSYCHIC, 0.40),
    (VibemonTypeT.DARK, 0.35),
)
NEW_MOON_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.GHOST, 0.35),
    (VibemonTypeT.DARK, 0.30),
)

# Sun below nautical twilight (-12°) marks deep night; above the horizon in the
# day band marks open daylight.
DEEP_NIGHT_SUN_ALTITUDE_DEG: Final[float] = -12.0
DEEP_NIGHT_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.DARK, 0.25),
    (VibemonTypeT.GHOST, 0.20),
    (VibemonTypeT.PSYCHIC, 0.15),
)
DAYTIME_SUN_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.ELECTRIC, 0.20),
    (VibemonTypeT.FLYING, 0.20),
)

# Deep night with no naked-eye planet above the horizon.
BARE_SKY_GHOST_BOOST: Final[float] = 0.25

# Moon growth/recession and seasonal arcs are deliberately asymmetric so no two
# sky types are score-degenerate: waxing leans grass (growth), midsummer leans
# fire (heat), waning leans water (recession), midwinter leans ice (chill).
MOON_GROWTH_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.GRASS, 0.28),
    (VibemonTypeT.FIRE, 0.22),
)
MOON_RECESSION_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.WATER, 0.28),
    (VibemonTypeT.ICE, 0.22),
)
SEASONAL_MIDSUMMER_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.FIRE, 0.25),
    (VibemonTypeT.GRASS, 0.15),
)
SEASONAL_MIDWINTER_ELEMENTS: Final[tuple[tuple[VibemonTypeT, float], ...]] = (
    (VibemonTypeT.ICE, 0.25),
    (VibemonTypeT.ROCK, 0.22),
)

SEASONAL_SUN_ARC_DEGREES: Final[float] = 15.0
TWILIGHT_MOON_PHASE_DAMPING: Final[float] = 0.65
TWILIGHT_MOON_DAMPING_FLOOR: Final[float] = 0.35
TIGHT_ASPECT_MAX_ORB: Final[float] = 3.0

# ── Creature visual cues per observed sky signal ──────────────────────────────────

MOON_VISUALS: Final[dict[MoonBucketT, str]] = {
    "full": "pale silver full-moon disc marking, moonlit sheen along the back",
    "new": "matte charcoal new-moon shading, shadow-soft outlines",
    "waxing_crescent": "slim waxing-crescent marking, silver-tipped edges",
    "waxing_gibbous": "bright waxing-gibbous patch, silver-washed flank",
    "waning_gibbous": "soft waning-gibbous patch, dimmed silver flank wash",
    "waning_crescent": "thin waning-crescent marking, ash-silver tips",
}

SOLAR_PHASE_VISUALS: Final[dict[generation_types.SolarPhase, str]] = {
    generation_types.SolarPhase.DAWN: "rose-gold dawn blush on the crest",
    generation_types.SolarPhase.DAY: "clear daylight glints across the brow",
    generation_types.SolarPhase.DUSK: "ember dusk edging along the silhouette",
    generation_types.SolarPhase.NIGHT: "deep night-blue undertones, star-fleck speckling",
}

SEASON_VISUALS: Final[dict[SeasonArcT, str]] = {
    "midsummer": "sun-warmed highlights",
    "midwinter": "frost-rimmed edges",
}

ECLIPSE_VISUAL: Final[str] = "dusky eclipse ring marking"
