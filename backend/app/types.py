"""Domain vocabularies, constrained types, and type aliases.

Use this module for units of meaning such as enums and aliases, not data
objects, persistence models, or runtime workflows.
"""

from typing import Annotated, Literal, TypedDict, NotRequired
from annotated_types import Len
import enum
import random
import uuid

from PIL.Image import Image


type TrainerIdT = Annotated[uuid.UUID, "backend trainer identifier"]
type BaseStatT = Annotated[int, "a clamped value between [5, 255]"]
type UnitIntervalT = Annotated[float, "a clamped value between [0, 1]"]
type BaseStatNameT = Literal["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
type StatStageNameT = Literal["attack", "defense", "sp_attack", "sp_defense", "speed", "accuracy", "evasion"]
type IdentityElementsT = Annotated[tuple[VibemonTypeT, ...], Len(min_length=1, max_length=2)]

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


class BattleRole(enum.Enum):
    """Battle role classifications based on stat distribution."""

    OFFENSIVE_GLASS_CANNON = "Extreme speed and power but fragile — must OHKO or faint."
    OFFENSIVE_SWEEPER = "Fast and powerful — designed to sweep weakened teams."
    OFFENSIVE_WALLBREAKER = "Slow but devastating — breaks through defensive Pokemon."
    OFFENSIVE_REVENGE_KILLER = "Fast cleaner designed to pick off weakened opponents."
    DEFENSIVE_WALL = "A resilient wall designed to soak hits on one or both sides."
    DEFENSIVE_TANK = "A defensive tank that can absorb hits and fight back."
    DEFENSIVE_STALLER = "A slow but durable staller that outlasts opponents."
    UTILITY_PIVOT = "A balanced pivot that switches out to maintain momentum."
    UTILITY_CLERIC = "A support-focused role that heals and clears status."
    UTILITY = "A balanced utility role that supports the team."

    @property
    def description(self) -> str:
        return self.value

    @property
    def category(self) -> str:
        """OFFENSIVE / DEFENSIVE / UTILITY — derived from the role name."""
        category, _, _ = self.name.partition("_")
        return category


class EvolutionStageT(enum.IntEnum):
    """The evolution stages."""

    BASE = 1
    STAGE_2 = 2
    STAGE_3 = 3
    PSUEDO_LEGENDARY = 10

    # DEV NOTE: RESERVED FOR SPECIAL EVENTS
    LEGENDARY = 20
    ULTRA_LEGENDARY = 99

    @classmethod
    def random_seed(cls, *, rng: random.Random | None = None) -> EvolutionStageT:
        stages = [cls.BASE, cls.STAGE_2, cls.STAGE_3, cls.PSUEDO_LEGENDARY]
        rarity = [24, 41, 34, 1]
        chooser = rng if rng is not None else random
        return chooser.choices(stages, rarity, k=1)[0]


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


class ActionTypeT(enum.StrEnum):
    """Actions a trainer can take during their turn."""

    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"


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


class SpriteLayout(TypedDict):
    """The types of sprites that a Vibemon can be generated in."""

    # ROW 1
    sheet: NotRequired[Image]

    # ROW 1
    battle_back: Image
    battle_hero: Image
    battle_opponent: Image

    # ROW 2
    emote_resting: Image
    emote_happy: Image
    emote_frustrated: Image

    # ROW 3
    emote_proud: Image
    emote_confused: Image
    emote_sad: Image
