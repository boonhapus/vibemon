from __future__ import annotations

from app.providers.base import VibemonProvider
from app.providers.spotify import SpotifyProvider
from app.providers.weather import WeatherProvider

PROVIDER_REGISTRY: list[type[VibemonProvider]] = [
    WeatherProvider,
    SpotifyProvider,
]

__all__ = ["PROVIDER_REGISTRY", "WeatherProvider", "SpotifyProvider"]
