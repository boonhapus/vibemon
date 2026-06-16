"""Progression vocabulary for Vibemon XP and evolution."""

import enum


class GrowthGroupT(enum.StrEnum):
    """Born maturation pace; drives the XP curve and evolution milestone levels."""

    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
