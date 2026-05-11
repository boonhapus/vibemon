"""
Color palette constants for the Vibemon UI, sprite generation, and battle system.

All colors are period-accurate to the 1960s-70s aesthetic defined in DESIGN.md.
See DESIGN.md §2 for the full rationale and historical references.

Organization mirrors the design document:
  - §2.1 Core Palette        → MUSTARD_YELLOW, AVOCADO_GREEN, etc.
  - §2.2 Vibemon Type Colors → TYPE_COLORS[VibemonTypeT.FIRE]
  - §2.3 Status Colors       → STATUS_HEALTHY / CAUTION / CRITICAL
"""
from collections.abc import Iterable
from typing import Final, NamedTuple
import functools as ft

from app.types import VibemonTypeT


class Color(NamedTuple):
    """A period-accurate color with display name and historical reference.

    The ``name`` and ``reference`` fields aren't decorative — they're consumed by
    the sprite-generation prompt (where descriptive context measurably improves
    image-model output) and by the debug overlay tooltips.
    """

    hex: str
    name: str
    reference: str = ""

    def __str__(self) -> str:
        return self.hex


# ============================================================================
# §2.1 Core Palette — UI chrome, structural elements, accents
# ============================================================================

MUSTARD_YELLOW: Final = Color("#E1AD01", "Mustard Yellow", "Highlights, selection cursors, health bars")
AVOCADO_GREEN:  Final = Color("#568203", "Avocado Green",  "Background environments, stat bars")
BURNT_ORANGE:   Final = Color("#CC5500", "Burnt Orange",   "Menus, flame accents")
TOBACCO_BROWN:  Final = Color("#3D2B1F", "Tobacco Brown",  "Text, borders, shadows")
CREAM:          Final = Color("#F5F5DC", "Cream/Eggshell", "Text boxes, background contrast")
GRAPE_PLUM:     Final = Color("#7C4D8A", "Grape Plum",     "Accent — psychedelic flourishes")

CORE_PALETTE: Final[tuple[Color, ...]] = (
    MUSTARD_YELLOW, AVOCADO_GREEN, BURNT_ORANGE,
    TOBACCO_BROWN, CREAM, GRAPE_PLUM,
)

# Lineart floor — never render lineart darker than this (DESIGN.md §6 / sprite prompt).
LINEART_FLOOR: Final = Color("#2A1E16", "Tobacco Black", "Hard floor for lineart darkness")

# Colors that the sprite prompt can produce regardless of elemental typing.
# Include these when choosing a chroma-key background; otherwise the solver can
# pick a key color that is far from the body fills but close to eyes, claws,
# highlights, or lineart.
SPRITE_CHROMA_PROTECTED_COLORS: Final[tuple[Color, ...]] = (
    TOBACCO_BROWN,
    LINEART_FLOOR,
    CREAM,
    MUSTARD_YELLOW,
    Color("#A03020", "Warm Red Detail Guard", "Common iris/accent color family"),
)


# ============================================================================
# §2.2 Vibemon Type Colors — elemental classifications
# ============================================================================

TYPE_COLORS: Final[dict[VibemonTypeT, Color]] = {
    VibemonTypeT.NORMAL:   Color("#C4A882", "Warm Parchment", "Aged paper, manila folders, linen upholstery"),
    VibemonTypeT.FIRE:     Color("#C0542A", "Terracotta",     "70s earthenware pottery, Southwestern ceramics"),
    VibemonTypeT.WATER:    Color("#3D8C8C", "Teal Mist",      "Mid-century aqua bathroom tile, Formica"),
    VibemonTypeT.ELECTRIC: Color("#D4A017", "Harvest Gold",   "Appliance gold, 70s kitchen hardware"),
    VibemonTypeT.GRASS:    Color("#6B7A2A", "Olive Drab",     "Army surplus, mid-century botanical illustration"),
    VibemonTypeT.ICE:      Color("#A0BAC8", "Powder Blue",    "60s leisure wear, institutional wall paint"),
    VibemonTypeT.FIGHTING: Color("#8B3A2A", "Brick Red",      "Exposed brick, Saltillo tile"),
    VibemonTypeT.POISON:   Color("#7C4D8A", "Grape Plum",     "Poison dart frogs, psychedelic ink prints"),
    VibemonTypeT.GROUND:   Color("#A0784A", "Sienna Sand",    "Southwest adobe, pre-Columbian pottery glaze"),
    VibemonTypeT.FLYING:   Color("#6E8FA8", "Slate Sky",      "Faded denim, horizon haze photography"),
    VibemonTypeT.PSYCHIC:  Color("#B0607A", "Dusty Orchid",   "Mod Op Art, pop-art poster ink"),
    VibemonTypeT.BUG:      Color("#7A8C2A", "Moss Khaki",     "Field guide illustration, olive cotton canvas"),
    VibemonTypeT.ROCK:     Color("#8C7A5A", "Warm Slate",     "Slate tile, mid-century stone veneer"),
    VibemonTypeT.GHOST:    Color("#524870", "Dusk Indigo",    "Kodachrome late-evening sky, Ektachrome shadows"),
    VibemonTypeT.DRAGON:   Color("#2A5C58", "Deep Verdigris", "Oxidized copper, brass-and-patina hardware"),
    VibemonTypeT.DARK:     Color("#4A3428", "Espresso",       "Dark-roast coffee, walnut veneer furniture"),
    VibemonTypeT.STEEL:    Color("#8A8C8E", "Pewter",         "Vintage Airstream aluminum, faded chrome"),
    VibemonTypeT.FAIRY:    Color("#C4909A", "Rose Quartz",    "Pastel cosmetics packaging, 50s–60s nursery pink"),
}


def status_color_for_hp(hp_fraction: float) -> Color:
    """Return the status color appropriate for a given HP fraction."""
    STATUS_HEALTHY:  Final = Color("#6B9B5A", "Sage",  "Full or near-full HP, OK state")
    STATUS_CAUTION:  Final = Color("#CC7A22", "Amber", "Mid-range HP, status conditions, warnings")
    STATUS_CRITICAL: Final = Color("#A03020", "Brick", "Low HP, fainted, critical errors")

    # HP fraction thresholds for status-color transitions (DESIGN.md §2.3).
    # Crossing a threshold downward changes the bar color.
    HP_THRESHOLD_CAUTION:  Final[float] = 0.50  # ≤ 50% of max → CAUTION
    HP_THRESHOLD_CRITICAL: Final[float] = 0.20  # ≤ 20% of max → CRITICAL

    match hp_fraction:
        case _ if hp_fraction <= HP_THRESHOLD_CRITICAL:
            return STATUS_CRITICAL
        case _ if hp_fraction <= HP_THRESHOLD_CAUTION:
            return STATUS_CAUTION
        case _:
            return STATUS_HEALTHY


# ============================================================================
# Background color solver — picks a candidate background that maximizes the
# minimum perceptual distance from a set of foreground colors, optimized for
# clean chroma-key separation in compositing pipelines.
#
# The default candidate pool is CHROMA_KEY_CANDIDATES — a curated set of
# colors spread across CIELAB space specifically for keying, NOT the brand
# palette. Chroma-key backgrounds get removed in compositing, so on-brand-ness
# is irrelevant; perceptual separation is what matters. Pass ``CORE_PALETTE``
# explicitly if you need an on-brand background that won't be keyed.
# ============================================================================


# Curated chroma-key candidate set. Selected for wide LAB-space coverage so
# the max-min algorithm always has a far candidate available regardless of
# foreground color. Includes industry-standard chroma green and blue, their
# complements, the warm/cool extremes, and luma-key endpoints for
# foregrounds that cluster near a single lightness band.
CHROMA_KEY_CANDIDATES: Final[tuple[Color, ...]] = (
    Color("#00B140", "Chroma Green",    "Industry-standard green-screen key"),
    Color("#0047AB", "Chroma Blue",     "Industry-standard blue-screen key"),
    Color("#C71585", "Chroma Magenta",  "Saturated complement to green"),
    Color("#FFD700", "Chroma Gold",     "Saturated complement to blue"),
    Color("#FF1744", "Chroma Red",      "Saturated warm extreme"),
    Color("#00E5FF", "Chroma Cyan",     "Saturated cool extreme"),
    Color("#1A1A2E", "Chroma Charcoal", "Luma key — dark endpoint"),
    Color("#F0F0F5", "Chroma Snow",     "Luma key — light endpoint"),
)


def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    """Convert ``"#RRGGBB"`` to sRGB floats in [0.0, 1.0]."""
    h = hex_str.lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _hex_to_hue(hex_str: str) -> float:
    """Return hue angle in degrees (0-360) from a hex color string."""
    r, g, b = _hex_to_rgb(hex_str)
    mx = max(r, g, b)
    mn = min(r, g, b)
    if mx == mn:
        return 0.0
    delta = mx - mn
    if mx == r:
        return 60.0 * (((g - b) / delta) % 6)
    elif mx == g:
        return 60.0 * (((b - r) / delta) + 2)
    else:
        return 60.0 * (((r - g) / delta) + 4)


@ft.cache
def _rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """Convert sRGB in [0, 1] to CIELAB (D65 illuminant).

    Uses the standard sRGB → linear RGB → XYZ → LAB chain. CIELAB is chosen
    because Euclidean distance in LAB approximates perceived color difference
    far better than distance in RGB or HSV — and chroma-key cleanliness is
    fundamentally about *perceived* separation, not RGB-vector separation.
    """
    # sRGB gamma decode → linear RGB
    def _linearize(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _linearize(rgb[0]), _linearize(rgb[1]), _linearize(rgb[2])

    # Linear RGB → XYZ (sRGB primaries, D65 white point)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    # Normalize by D65 reference white
    x, y, z = x / 0.95047, y / 1.00000, z / 1.08883

    # XYZ → LAB
    _DELTA = 6.0 / 29.0

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > _DELTA**3 else t / (3 * _DELTA**2) + 4 / 29

    fx, fy, fz = _f(x), _f(y), _f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def _delta_e_76(lab1: tuple[float, float, float], lab2: tuple[float, float, float]) -> float:
    """
    CIE76 perceptual color difference. Euclidean distance in LAB space.

    CIE76 is less accurate than CIE2000 near very saturated colors, but
    for this application the difference is negligible and CIE76 is much
    simpler to reason about.
    """
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5


def solve_background_color(
    *foreground_colors: Color,
    candidates: Iterable[Color] = CHROMA_KEY_CANDIDATES,
    hue_protected: Iterable[Color] = (),
) -> Color:
    """
    Choose the candidate background most perceptually distant from every
    foreground color, optimized for clean chroma-key separation.

    Uses a max-min strategy: each candidate is scored by its *minimum*
    ΔE76 distance to any foreground color, and the candidate with the
    highest such minimum wins. This guarantees no foreground color sits
    closer than necessary to the chosen background — important because a
    chroma-keyer fails on the foreground color closest to the key, not
    the average.

    The max-min strategy is preferred over computing a "perceptual
    opposite" of the centroid because the centroid loses information
    when foreground colors are themselves spread out: the centroid of
    Fire and Flying is neutral gray, and the opposite of neutral gray
    is also neutral gray — close to one of the inputs. Max-min over a
    candidate pool sidesteps this entirely by considering each
    foreground independently.

    Any candidate whose hex matches a foreground color is excluded
    automatically — you cannot key a background away from itself.

    ``hue_protected`` specifies colors whose hue family should not overlap
    with the chosen background. When the AI sprite model generates hues
    in the same family as a type color (e.g. water's teal), a chroma-key
    background in that same hue region (e.g. Chroma Blue) may erase
    sprite elements even though the exact hex isn't in the foreground
    set. Candidates whose hue is within 50° of any hue-protected color
    are skipped unless no candidate passes the filter, in which case the
    max-min winner from the full pool is used.

    Examples:
        >>> # Single-typed Fire creature, chroma-key default
        >>> solve_background_color(TYPE_COLORS[VibemonTypeT.FIRE]).name
        'Chroma Cyan'

        >>> # Dual-typed Fire/Flying — max-min handles diverse foregrounds
        >>> solve_background_color(
        ...     TYPE_COLORS[VibemonTypeT.FIRE],
        ...     TYPE_COLORS[VibemonTypeT.FLYING],
        ... ).name
        'Chroma Magenta'

        >>> # On-brand background for non-keyed display
        >>> solve_background_color(
        ...     TYPE_COLORS[VibemonTypeT.FIRE],
        ...     candidates=CORE_PALETTE,
        ... ).name
        'Avocado Green'
    """
    if not foreground_colors:
        raise ValueError("solve_background_color requires at least one foreground color")

    fg_labs = [_rgb_to_lab(_hex_to_rgb(c.hex)) for c in foreground_colors]
    fg_hex_set = {c.hex.upper() for c in foreground_colors}

    protected_hues = {_hex_to_hue(c.hex) for c in hue_protected}

    def _hue_filtered(candidates: list[Color]) -> list[Color]:
        if not protected_hues:
            return list(candidates)
        result: list[Color] = []
        for c in candidates:
            ch = _hex_to_hue(c.hex)
            if any(min(abs(ch - ph), 360 - abs(ch - ph)) < 50 for ph in protected_hues):
                continue
            result.append(c)
        return result

    candidate_list = list(candidates)
    filtered = _hue_filtered(candidate_list)
    pool = filtered if filtered else candidate_list

    best: Color | None = None
    best_score = -1.0

    for candidate in pool:
        if candidate.hex.upper() in fg_hex_set:
            continue

        cand_lab = _rgb_to_lab(_hex_to_rgb(candidate.hex))

        min_dist = min(_delta_e_76(cand_lab, fg_lab) for fg_lab in fg_labs)

        if min_dist > best_score:
            best_score = min_dist
            best = candidate

    if best is None:
        raise ValueError(
            f"No background candidates remain after filtering foreground "
            f"colors {[c.hex for c in foreground_colors]} from candidate pool"
        )

    return best


def sprite_foreground_colors(elements: Iterable[VibemonTypeT]) -> tuple[Color, ...]:
    """Return all expected sprite foreground colors for chroma-key solving."""
    colors = [TYPE_COLORS[element] for element in elements]
    colors.extend(SPRITE_CHROMA_PROTECTED_COLORS)
    return tuple(colors)


# ============================================================================
# Drift detection — fail fast at import time if the type→color map gets out
# of sync with the VibemonTypeT enum. Cheaper to crash on import than to
# render a battle UI with a missing color mid-game.
# ============================================================================

assert set(TYPE_COLORS.keys()) == set(VibemonTypeT), (
    f"TYPE_COLORS is out of sync with VibemonTypeT. "
    f"Missing: {set(VibemonTypeT) - set(TYPE_COLORS.keys())}, "
    f"Extra: {set(TYPE_COLORS.keys()) - set(VibemonTypeT)}"
)
