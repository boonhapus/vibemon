from typing import Annotated
import enum
import uuid

import attrs

from app import const


type TrainerId = Annotated[uuid.UUID, "backend trainer identifier"]
type BaseStat = Annotated[int, "a positive integer within the range [5, 255]"]


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


class ActionType(str, enum.Enum):
    """Actions a trainer can take during their turn."""

    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"


# ── Stats ────────────────────────────────────────────────────────────────────────────


@attrs.define
class StatStages:
    """Stat stage modifiers accumulated during battle, ranging from -6 to +6."""

    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


# ── Move ────────────────────────────────────────────────────────────────────────────


@attrs.define
class MoveEffect:
    """Secondary effects that may occur when a move is used."""

    status_inflict: StatusConditionT | None = None
    stat_changes: dict[str, int] = attrs.field(factory=dict)
    target_self: bool = False
    chance: float = 1.0


@attrs.define(eq=False)
class Move:
    """A move that a Vibemon can learn and use in battle."""

    name: str
    flavor_text: str
    type: VibemonTypeT
    category: MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0
    pp: int = const.PP_DEFAULT
    effect: MoveEffect | None = None

    pp_current: int = const.PP_DEFAULT
    priority: int = 0
    crit_ratio: int = 0
    target: MoveTargetT = MoveTargetT.SINGLE

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)


# ── Action ────────────────────────────────────────────────────────────────────────────


@attrs.define
class Action:
    """An action selected by a trainer to perform during their turn."""

    trainer_name: TrainerId
    action_type: ActionType
    value: str
