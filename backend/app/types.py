from typing import Annotated, Literal
import enum
import uuid

type TrainerIdT = Annotated[uuid.UUID, "backend trainer identifier"]
type BaseStatT = Annotated[int, "a clamped value between [5, 255]"]
type BaseStatNameT = Literal["attack", "defense", "sp_attack", "sp_defense", "speed", "accuracy", "evasion"]

# ── Enums ────────────────────────────────────────────────────────────────────────────


class VibemonTypeT(str, enum.Enum):
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


class StatusConditionT(str, enum.Enum):
    """Status conditions that can affect a Vibemon during battle."""

    NONE = "none"
    BURN = "burn"
    POISON = "poison"
    BAD_POISON = "bad_poison"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    FAINTED = "fainted"


class MoveCategoryT(str, enum.Enum):
    """Categorization of moves based on their battle effect."""

    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class MoveTargetT(str, enum.Enum):
    """Valid targets for a move during battle."""

    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"


class WeatherT(str, enum.Enum):
    """Battle weather conditions that affect certain Vibemon types."""

    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


class ActionTypeT(str, enum.Enum):
    """Actions a trainer can take during their turn."""

    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"
