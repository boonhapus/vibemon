"""Ephemeris and chart data types for the celestial provider."""

import functools as ft

from app.core.schema import FrozenSchema
from app.domains.generation import types as generation_types


class BodyObservation(FrozenSchema):
    name: str
    ecliptic_longitude: float
    altitude_deg: float
    visible: bool
    house: int
    sign: str


class AspectObservation(FrozenSchema):
    body_a: str
    body_b: str
    aspect: str
    orb_deg: float


class CelestialChart(FrozenSchema):
    # Provenance: identifies the birth a persisted payload was captured for.
    timestamp_iso: str
    latitude: float
    longitude: float
    timezone: str

    solar_phase: generation_types.SolarPhase
    twilight_prevalence: float
    moon_illumination: float
    eclipse_season: bool
    house_cusps: tuple[float, ...]
    bodies: tuple[BodyObservation, ...]
    aspects: tuple[AspectObservation, ...]

    @ft.cached_property
    def bodies_by_name(self) -> dict[str, BodyObservation]:
        return {body.name: body for body in self.bodies}
