"""Celestial provider fetch/synthesize payload."""

from app.providers import schema as providers_schema
from app.providers.celestial.ephemeris import models


class CelestialPayload(providers_schema.ProviderPayload):
    chart: models.CelestialChart
