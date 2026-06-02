"""Provider contract schemas for payloads, notes, and stat synthesis."""

from typing import cast
import enum

from app.core.schema import FrozenSchema
from app.core.types import UnitIntervalT
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import BaseStats
from app.domains.vibemon.strength_formulas import base_stat_asymmetric_scaling, stat_ratio_from_grade
from app.domains.vibemon.types import BaseStatNameT


class ProviderNoteLevelT(enum.StrEnum):
    """Severity for provider-originated birth notes."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProviderNote(FrozenSchema):
    """Structured note attached to a captured provider payload or birth affinity."""

    level: ProviderNoteLevelT
    code: str
    message: str


class ProviderPayloadMeta(FrozenSchema):
    """Shared metadata envelope for every persisted provider payload."""

    notes: tuple[ProviderNote, ...] = ()


class ProviderPayload(FrozenSchema):
    """
    Base shape for provider-owned fetch/synthesize payloads.

    This is intended to be inherited from.
    """

    meta: ProviderPayloadMeta = ProviderPayloadMeta()


class BaseStatCenters(FrozenSchema):
    """
    Normalized middle-anchored unit intervals per base stat axis (0.0-1.0).

    0.5 means "typical for the Provider signal's global range", not necessarily
    the 'median' or 'mean'.
    """

    hp: UnitIntervalT
    attack: UnitIntervalT
    defense: UnitIntervalT
    sp_attack: UnitIntervalT
    sp_defense: UnitIntervalT
    speed: UnitIntervalT

    def scaled(self, *, elements: tuple[VibemonTypeT, ...]) -> BaseStats:
        """Apply type-grade bands and asymmetric BST scaling to BaseStatCenters."""
        translated: dict[BaseStatNameT, int] = {}

        for stat_name in ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed"):
            stat = cast(UnitIntervalT, getattr(self, stat_name, 0.5))
            scaled = stat_ratio_from_grade(stat, elements=elements, stat=stat_name)
            translated[stat_name] = base_stat_asymmetric_scaling(scaled, stat=stat_name)

        return BaseStats(**translated)
