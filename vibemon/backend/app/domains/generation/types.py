import enum


class SolarPhase(enum.StrEnum):
    """Local solar-time phase derived from coordinates and timestamp."""

    DAWN = "dawn"
    DAY = "day"
    DUSK = "dusk"
    NIGHT = "night"
