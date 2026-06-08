"""Celestial birth provider catalog stub."""

from typing import ClassVar

from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers.catalog_support import GEOLOCATION_REQUIREMENT, UnimplementedProvider


class CelestialProvider(UnimplementedProvider):
    """
    A Vibemon is born from the sky above its birthplace at the birth moment.

    One hatched under a full moon over open desert reads differently from one
    under a dawn conjunction above city haze - same hour on the clock, different
    light on the horizon.
    """

    name = "celestial"
    display_label = "STARS"
    tagline = "Moonlight, horizon light, and the chart at birth."
    data_sources = (
        catalog.DataSourceInfo(
            name="Ephemeris computation",
            description="Offline sky chart from birth timestamp and coordinates.",
        ),
    )
    requirements = (GEOLOCATION_REQUIREMENT,)
    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.ELECTRIC, "daytime sun above the horizon"),
        (VibemonTypeT.FLYING, "daytime sun above the horizon"),
        (VibemonTypeT.GHOST, "deep night or low moon illumination"),
        (VibemonTypeT.DARK, "night sky and waning moon phases"),
        (VibemonTypeT.PSYCHIC, "full moon and stacked visible planets"),
        (VibemonTypeT.FAIRY, "twilight and civil dawn"),
        (VibemonTypeT.FIRE, "midsummer sun and waxing moon growth"),
        (VibemonTypeT.GRASS, "waxing moon growth phase"),
        (VibemonTypeT.WATER, "waning moon recession"),
        (VibemonTypeT.ICE, "midwinter solar phase"),
        (VibemonTypeT.ROCK, "midwinter solar phase and Saturn visibility"),
        (VibemonTypeT.DRAGON, "Jupiter visibility above the horizon"),
    ]
