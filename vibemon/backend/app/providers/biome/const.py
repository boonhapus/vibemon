"""Biome provider constants: WorldCover taxonomy, scoring tables, and flavor text."""

from dataclasses import dataclass
from typing import Final, Self
import enum

from app.domains.generation import types as generation_types
from app.domains.move.types import VibemonTypeT

type StatTierT = str


@dataclass(frozen=True, slots=True)
class WorldCoverProfile:
    """Per-class WorldCover scoring, flavor, and raster legend metadata."""

    rgb: tuple[int, int, int]
    flavor: str
    stat_archetype: dict[str, StatTierT]
    base_weights: dict[VibemonTypeT, float]
    water_proximity_gate: float


class WorldCoverClassT(enum.StrEnum):
    """ESA WorldCover 2021 land-cover classes."""

    TREE_COVER = "tree_cover"
    SHRUBLAND = "shrubland"
    GRASSLAND = "grassland"
    CROPLAND = "cropland"
    BUILT_UP = "built_up"
    BARE_SPARSE = "bare_sparse"
    SNOW_ICE = "snow_ice"
    PERMANENT_WATER = "permanent_water"
    HERBACEOUS_WETLAND = "herbaceous_wetland"
    MANGROVES = "mangroves"
    MOSS_LICHEN = "moss_lichen"

    @property
    def profile(self) -> WorldCoverProfile:
        return WORLD_COVER_PROFILES[self]

    @classmethod
    def nearest_rgb(cls, rgb: tuple[int, int, int]) -> tuple[Self, int]:
        best_class: WorldCoverClassT = cls.PERMANENT_WATER
        best_distance = 10**9
        for land_cover in cls:
            legend_rgb = land_cover.profile.rgb
            distance = sum((channel - legend) ** 2 for channel, legend in zip(rgb, legend_rgb, strict=True))
            if distance < best_distance:
                best_distance = distance
                best_class = land_cover
        return best_class, best_distance


WORLD_COVER_PROFILES: Final[dict[WorldCoverClassT, WorldCoverProfile]] = {
    WorldCoverClassT.TREE_COVER: WorldCoverProfile(
        rgb=(0, 100, 0),
        flavor="born under a green cathedral of leaves",
        stat_archetype={
            "hp": "+",
            "sp_defense": "+",
            "speed": "-",
            "sp_attack": "-",
            "attack": "0",
            "defense": "0",
        },
        base_weights={
            VibemonTypeT.GRASS: 0.55,
            VibemonTypeT.BUG: 0.50,
            VibemonTypeT.GHOST: 0.35,
            VibemonTypeT.FLYING: 0.30,
            VibemonTypeT.NORMAL: 0.25,
        },
        water_proximity_gate=0.22,
    ),
    WorldCoverClassT.SHRUBLAND: WorldCoverProfile(
        rgb=(255, 187, 34),
        flavor="born among sun-warmed scrub and thicket",
        stat_archetype={
            "attack": "+",
            "defense": "+",
            "sp_attack": "-",
            "sp_defense": "-",
            "hp": "0",
            "speed": "0",
        },
        base_weights={
            VibemonTypeT.GROUND: 0.45,
            VibemonTypeT.FIRE: 0.35,
            VibemonTypeT.FIGHTING: 0.30,
            VibemonTypeT.NORMAL: 0.25,
        },
        water_proximity_gate=0.20,
    ),
    WorldCoverClassT.GRASSLAND: WorldCoverProfile(
        rgb=(255, 255, 76),
        flavor="born in open meadow wind and grazing light",
        stat_archetype={
            "speed": "+",
            "attack": "+",
            "defense": "-",
            "sp_defense": "-",
            "hp": "0",
            "sp_attack": "0",
        },
        base_weights={
            VibemonTypeT.GRASS: 0.50,
            VibemonTypeT.NORMAL: 0.45,
            VibemonTypeT.BUG: 0.35,
            VibemonTypeT.FLYING: 0.30,
        },
        water_proximity_gate=0.18,
    ),
    WorldCoverClassT.CROPLAND: WorldCoverProfile(
        rgb=(240, 150, 255),
        flavor="born where rows and furrows shape the horizon",
        stat_archetype={
            "hp": "+",
            "defense": "+",
            "attack": "-",
            "sp_attack": "-",
            "sp_defense": "0",
            "speed": "0",
        },
        base_weights={
            VibemonTypeT.GRASS: 0.45,
            VibemonTypeT.BUG: 0.45,
            VibemonTypeT.NORMAL: 0.40,
            VibemonTypeT.FLYING: 0.25,
        },
        water_proximity_gate=0.18,
    ),
    WorldCoverClassT.BUILT_UP: WorldCoverProfile(
        rgb=(250, 0, 0),
        flavor="born in the hum of streets and stone",
        stat_archetype={
            "speed": "+",
            "sp_attack": "+",
            "hp": "-",
            "sp_defense": "-",
            "attack": "0",
            "defense": "0",
        },
        base_weights={
            VibemonTypeT.STEEL: 0.55,
            VibemonTypeT.ELECTRIC: 0.50,
            VibemonTypeT.DARK: 0.45,
            VibemonTypeT.NORMAL: 0.40,
            VibemonTypeT.POISON: 0.35,
        },
        water_proximity_gate=0.56,
    ),
    WorldCoverClassT.BARE_SPARSE: WorldCoverProfile(
        rgb=(180, 180, 180),
        flavor="born in the wide bone-dry quiet",
        stat_archetype={
            "attack": "+",
            "speed": "+",
            "sp_defense": "-",
            "hp": "-",
            "defense": "0",
            "sp_attack": "0",
        },
        base_weights={
            VibemonTypeT.GROUND: 0.55,
            VibemonTypeT.FIRE: 0.45,
            VibemonTypeT.ROCK: 0.35,
            VibemonTypeT.NORMAL: 0.25,
        },
        water_proximity_gate=0.15,
    ),
    WorldCoverClassT.SNOW_ICE: WorldCoverProfile(
        rgb=(240, 240, 240),
        flavor="born where the wind stops being warm",
        stat_archetype={
            "defense": "+",
            "sp_defense": "+",
            "speed": "-",
            "attack": "-",
            "hp": "0",
            "sp_attack": "0",
        },
        base_weights={
            VibemonTypeT.ICE: 0.60,
            VibemonTypeT.ROCK: 0.35,
            VibemonTypeT.NORMAL: 0.20,
        },
        water_proximity_gate=0.25,
    ),
    WorldCoverClassT.PERMANENT_WATER: WorldCoverProfile(
        rgb=(0, 100, 200),
        flavor="born at the mirror of still water",
        stat_archetype={
            "sp_attack": "+",
            "speed": "+",
            "defense": "-",
            "attack": "-",
            "hp": "0",
            "sp_defense": "0",
        },
        base_weights={
            VibemonTypeT.WATER: 0.65,
            VibemonTypeT.ICE: 0.25,
            VibemonTypeT.NORMAL: 0.20,
        },
        water_proximity_gate=1.0,
    ),
    WorldCoverClassT.HERBACEOUS_WETLAND: WorldCoverProfile(
        rgb=(0, 150, 160),
        flavor="born where reeds drink standing water",
        stat_archetype={
            "sp_defense": "+",
            "sp_attack": "+",
            "attack": "-",
            "defense": "-",
            "hp": "0",
            "speed": "0",
        },
        base_weights={
            VibemonTypeT.WATER: 0.50,
            VibemonTypeT.POISON: 0.45,
            VibemonTypeT.GRASS: 0.40,
            VibemonTypeT.BUG: 0.35,
        },
        water_proximity_gate=0.85,
    ),
    WorldCoverClassT.MANGROVES: WorldCoverProfile(
        rgb=(0, 207, 117),
        flavor="born where roots hold salt and tide",
        stat_archetype={
            "hp": "+",
            "sp_attack": "+",
            "speed": "-",
            "attack": "-",
            "defense": "0",
            "sp_defense": "0",
        },
        base_weights={
            VibemonTypeT.WATER: 0.50,
            VibemonTypeT.GRASS: 0.45,
            VibemonTypeT.BUG: 0.35,
            VibemonTypeT.POISON: 0.30,
        },
        water_proximity_gate=0.85,
    ),
    WorldCoverClassT.MOSS_LICHEN: WorldCoverProfile(
        rgb=(250, 230, 160),
        flavor="born on slow stone dressed in lichen",
        stat_archetype={
            "sp_defense": "+",
            "defense": "+",
            "attack": "-",
            "speed": "-",
            "hp": "0",
            "sp_attack": "0",
        },
        base_weights={
            VibemonTypeT.ROCK: 0.45,
            VibemonTypeT.ICE: 0.40,
            VibemonTypeT.FAIRY: 0.30,
            VibemonTypeT.NORMAL: 0.25,
        },
        water_proximity_gate=0.20,
    ),
}

assert set(WORLD_COVER_PROFILES) == set(WorldCoverClassT)

STAT_TIER_CENTER: Final[dict[StatTierT, float]] = {"+": 0.75, "0": 0.5, "-": 0.25}

SOLAR_PHASE_BONUS: Final[dict[generation_types.SolarPhase, dict[VibemonTypeT, float]]] = {
    generation_types.SolarPhase.DAWN: {VibemonTypeT.FAIRY: 0.20, VibemonTypeT.PSYCHIC: 0.15},
    generation_types.SolarPhase.DAY: {VibemonTypeT.FIRE: 0.15, VibemonTypeT.FLYING: 0.15},
    generation_types.SolarPhase.DUSK: {VibemonTypeT.GHOST: 0.20, VibemonTypeT.FAIRY: 0.15},
    generation_types.SolarPhase.NIGHT: {VibemonTypeT.DARK: 0.25, VibemonTypeT.GHOST: 0.20},
}

URBAN_ELEMENT_WEIGHTS: Final[dict[VibemonTypeT, float]] = {
    VibemonTypeT.STEEL: 0.35,
    VibemonTypeT.ELECTRIC: 0.30,
    VibemonTypeT.DARK: 0.25,
    VibemonTypeT.POISON: 0.20,
    VibemonTypeT.NORMAL: 0.15,
}

NATURAL_ELEMENT_WEIGHTS: Final[dict[VibemonTypeT, float]] = {
    VibemonTypeT.GRASS: 0.25,
    VibemonTypeT.BUG: 0.20,
    VibemonTypeT.GROUND: 0.20,
    VibemonTypeT.NORMAL: 0.15,
}

HIGH_ELEVATION_ELEMENT_WEIGHTS: Final[dict[VibemonTypeT, float]] = {
    VibemonTypeT.ROCK: 0.30,
    VibemonTypeT.ICE: 0.25,
    VibemonTypeT.FLYING: 0.25,
    VibemonTypeT.DRAGON: 0.20,
}

INTENSITY: Final[float] = 0.5

MARINE_WATER_REACH_KM: Final[float] = 50.0
INLAND_WATER_REACH_KM: Final[float] = 15.0
MARINE_FEATURE_BONUS: Final[float] = 0.08
INLAND_FEATURE_BONUS: Final[float] = 0.06
LAKE_FEATURE_BONUS: Final[float] = 0.08

# Extra water affinity when urban fabric sits on immediate coast or canal frontage.
BUILT_UP_CLOSE_WATER_THRESHOLD: Final[float] = 0.85
BUILT_UP_CLOSE_WATER_BONUS: Final[float] = 0.22
