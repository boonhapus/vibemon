from __future__ import annotations

from app.infra.providers.protocol import VibemonProvider
from app.infra.providers.spotify import SpotifyProvider
from app.infra.providers.weather import WeatherProvider

PROVIDER_REGISTRY: list[type[VibemonProvider]] = [
    WeatherProvider,
    SpotifyProvider,
]

__all__ = ["PROVIDER_REGISTRY", "WeatherProvider", "SpotifyProvider"]
