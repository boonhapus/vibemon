"""Vibemon identity, lifecycle, and presentation vocabularies."""

from typing import Annotated, Literal, Self
import enum
import random

from annotated_types import Len

from app.domains.move.types import VibemonTypeT

type BaseStatT = Annotated[int, "a clamped value between [5, 255]"]
type BaseStatNameT = Literal["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
type IdentityElementsT = Annotated[tuple[VibemonTypeT, ...], Len(min_length=1, max_length=2)]


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
    UTILITY = "A balanced utility role that supports the crew."

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
    PSEUDO_LEGENDARY = 10

    # DEV NOTE: RESERVED FOR SPECIAL EVENTS
    LEGENDARY = 20
    ULTRA_LEGENDARY = 99

    @classmethod
    def random_seed(cls, *, rng: random.Random | None = None) -> Self:
        stages = [cls.BASE, cls.STAGE_2, cls.STAGE_3, cls.PSEUDO_LEGENDARY]
        rarity = [24, 41, 34, 1]
        chooser = rng if rng is not None else random
        return chooser.choices(stages, rarity, k=1)[0]


class PoseT(enum.StrEnum):
    """The 9 poses extracted from a Vibemon's 3x3 sprite sheet."""

    BATTLE_BACK = "battle_back"
    BATTLE_HERO = "battle_hero"
    BATTLE_OPPONENT = "battle_opponent"
    EMOTE_RESTING = "emote_resting"
    EMOTE_HAPPY = "emote_happy"
    EMOTE_FRUSTRATED = "emote_frustrated"
    EMOTE_PROUD = "emote_proud"
    EMOTE_CONFUSED = "emote_confused"
    EMOTE_SAD = "emote_sad"


class VibemonLifecycleT(enum.StrEnum):
    """Lifecycle states for a Vibemon's asset realization."""

    BORN = "born"
    CHRISTENED = "christened"
    MANIFESTED = "manifested"
