from typing import Annotated
import attrs
import enum
import uuid


type TrainerId = Annotated[uuid.UUID, "backend trainer identifier"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VibemonT(str, enum.Enum):
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
    NONE = "none"
    BURN = "burn"
    POISON = "poison"
    BAD_POISON = "bad_poison"
    PARALYSIS = "paralysis"
    SLEEP = "sleep"
    FREEZE = "freeze"
    FAINTED = "fainted"


class MoveCategoryT(str, enum.Enum):
    PHYSICAL = "physical"
    SPECIAL = "special"
    STATUS = "status"


class MoveTargetT(str, enum.Enum):
    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"


class WeatherT(str, enum.Enum):
    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


class ActionType(str, enum.Enum):
    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@attrs.define
class BaseStats:
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


@attrs.define
class StatStages:
    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


# ---------------------------------------------------------------------------
# Move
# ---------------------------------------------------------------------------


@attrs.define
class MoveEffect:
    status_inflict: StatusConditionT | None = None
    stat_changes: dict[str, int] = attrs.field(factory=dict)
    target_self: bool = False
    chance: float = 1.0


@attrs.define
class Move:
    name: str
    type: VibemonT
    category: MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0
    pp: int = 10
    pp_current: int = 10
    priority: int = 0
    effect: MoveEffect | None = None
    makes_contact: bool = False
    target: MoveTargetT = MoveTargetT.SINGLE


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


@attrs.define
class Action:
    trainer_name: TrainerId
    action_type: ActionType
    value: str
