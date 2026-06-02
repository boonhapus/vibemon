"""Open-Meteo elevation client for biome place snapshots."""

from typing import Any
import datetime as dt

import niquests

from app.providers._api.hooks import LoggingHook, RateLimiterHook, ThrottledSessionMixin
from app.providers._api.policy import provider_default_headers, provider_retry_policy

from . import const


class OpenMeteoElevationClient(ThrottledSessionMixin, niquests.AsyncSession):
    """Point elevation lookup using Copernicus GLO-90 via Open-Meteo."""

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = RateLimiterHook(
            (600, dt.timedelta(minutes=1)),
            (5_000, dt.timedelta(hours=1)),
            provider=OpenMeteoElevationClient.provider_name,
            concurrency=1,
        )

        super().__init__(
            base_url=const.ELEVATION_BASE_URL,
            hooks=LoggingHook(provider=OpenMeteoElevationClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            headers=provider_default_headers(),
            **session_opts,
        )

    async def point(self, latitude: float, longitude: float) -> float:
        response = await self.get(
            const.ELEVATION_PATH,
            params={"latitude": str(latitude), "longitude": str(longitude)},
        )
        response.raise_for_status()
        payload = response.json()
        return float(payload["elevation"][0])
