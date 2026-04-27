from typing import Annotated, Literal, TypedDict, NotRequired
import enum
import uuid

from PIL import Image


type TrainerIdT = Annotated[uuid.UUID, "backend trainer identifier"]
type BaseStatT = Annotated[int, "a clamped value between [5, 255]"]
type BaseStatNameT = Literal["attack", "defense", "sp_attack", "sp_defense", "speed", "accuracy", "evasion"]

# ── Enums ────────────────────────────────────────────────────────────────────────────


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


class TierT(enum.StrEnum):
    """Tier classifications for Vibemon."""

    RUNT = "runt"
    MID = "mid"
    SOLID = "solid"
    APEX = "apex"
    MYTHIC = "mythic"


class EvolutionStageT(enum.IntEnum):
    """The evolution stages."""

    BASE = 1
    STAGE_1 = 2
    STAGE_2 = 3
    LEGENDARY = 10


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


class MoveTargetT(enum.StrEnum):
    """Valid targets for a move during battle."""

    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"


class WeatherT(enum.StrEnum):
    """Battle weather conditions that affect certain Vibemon types."""

    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


class ActionTypeT(enum.StrEnum):
    """Actions a trainer can take during their turn."""

    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"


class SpriteLayout(TypedDict):
    """The types of sprites that a Vibemon can be generated in."""

    sheet: NotRequired[Image.Image]
    perspective_player: Image.Image
    perspective_opponent: Image.Image
    showcase: Image.Image
