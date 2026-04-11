from __future__ import annotations

from app.providers.base import VibemonProvider
from app.providers.weather import WeatherProvider

PROVIDER_REGISTRY: list[type[VibemonProvider]] = [
    WeatherProvider,
]

__all__ = ["PROVIDER_REGISTRY", "WeatherProvider"]
