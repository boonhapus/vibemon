"""Open-Meteo elevation client for biome place snapshots."""

from typing import Any
import datetime as dt

from app.providers._api import rate_limits
from app.providers._api.hooks import LoggingHook, ThrottledSessionMixin
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.providers._api.session import CachedAPIClient
from app.providers.climate.openmeteo import const as openmeteo_quota
from app.storage.cache.redis import make_cache_backend

from . import const


class OpenMeteoElevationClient(ThrottledSessionMixin, CachedAPIClient):
    """Point elevation lookup using Copernicus GLO-90 via Open-Meteo."""

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = rate_limits.shared(
            openmeteo_quota.QUOTA_KEY,
            provider=OpenMeteoElevationClient.provider_name,
            limits=openmeteo_quota.RATE_LIMITS,
            concurrency=openmeteo_quota.CONCURRENCY,
        )

        session_opts.setdefault("backend", make_cache_backend("openmeteo_elevation_api"))
        super().__init__(
            expire_after=dt.timedelta(days=30),
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
