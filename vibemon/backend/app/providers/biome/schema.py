"""Biome provider fetch/synthesize payload."""

from app.providers import schema as providers_schema


class BiomePayload(providers_schema.ProviderPayload):
    land_cover_class: str
    built_up_fraction: float
    elevation_m: float
    solar_phase: str
    nearest_marine_km: float | None = None
    marine_feature: str | None = None
    nearest_inland_water_km: float | None = None
    inland_feature: str | None = None
