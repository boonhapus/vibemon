import enum

from app.core.schema import FrozenSchema


class SolarPhase(enum.StrEnum):
    """Local solar-time phase derived from coordinates and timestamp."""

    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"


class ProviderWarningLevel(enum.StrEnum):
    """Severity for Provider Warnings surfaced during candidate review."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ProviderWarning(FrozenSchema):
    """Domain-owned note a Provider attaches to a birth affinity."""

    level: ProviderWarningLevel
    code: str
    message: str
