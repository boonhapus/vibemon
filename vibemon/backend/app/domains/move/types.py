"""Move and elemental battle vocabularies."""

from typing import Literal
import enum

type StatStageNameT = Literal["attack", "defense", "sp_attack", "sp_defense", "speed", "accuracy", "evasion"]


class VibemonTypeT(enum.StrEnum):
    """Elemental type classifications for Vibemon species."""

    NORMAL = "normal"
    FIRE = "fire"
    WATER = "water"
    ELECTRIC = "electric"
    GRASS = "grass"
    ICE = "ice"
    FIGHTING = "fighting"
    POISON = "poison"
    GROUND = "ground"
    FLYING = "flying"
    PSYCHIC = "psychic"
    BUG = "bug"
    ROCK = "rock"
    GHOST = "ghost"
    DRAGON = "dragon"
    DARK = "dark"
    STEEL = "steel"
    FAIRY = "fairy"


class StatusConditionT(enum.StrEnum):
    """Status conditions that can affect a Vibemon during battle."""

    NONE = "none"
    BURN = "burn"
    POISON = "poison"
    BAD_POISON = "bad_poison"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    FAINTED = "fainted"


class MoveCategoryT(enum.StrEnum):
    """Categorization of moves based on their battle effect."""

    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class WeatherT(enum.StrEnum):
    """Battle field weather."""

    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


class MoveTargetT(enum.StrEnum):
    """Move target topology."""

    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"
    USER_SIDE = "user_side"
    OPPONENT_SIDE = "opponent_side"
    FIELD = "field"
