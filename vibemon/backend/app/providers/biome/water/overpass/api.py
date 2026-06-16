"""OSM Overpass client for marine and inland water proximity."""

from typing import Any
import asyncio
import datetime as dt

import niquests
import structlog

from app.providers._api.hooks import LoggingHook, RateLimiterHook
from app.providers._api.policy import provider_default_headers
from app.providers._api.session import CachedAPIClient
from app.storage.cache.redis import make_cache_backend

from . import const, utils

_LOGGER = structlog.get_logger(__name__)


class OverpassWaterClient(CachedAPIClient):
    """Nearest marine and inland water features via OSM Overpass."""

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = RateLimiterHook(
            (30, dt.timedelta(minutes=1)),
            provider=OverpassWaterClient.provider_name,
        )
        session_opts.setdefault("backend", make_cache_backend("overpass_water_api"))
        super().__init__(
            expire_after=dt.timedelta(days=30),
            hooks=LoggingHook(provider=OverpassWaterClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=niquests.RetryConfiguration(
                total=3,
                backoff_factor=2,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST"],
                raise_on_status=False,
                respect_retry_after_header=True,
            ),
            **session_opts,
        )
        self.headers.update(provider_default_headers())

    async def proximity(self, latitude: float, longitude: float) -> dict[str, Any]:
        radius = const.SEARCH_RADIUS_M
        marine_query = const.MARINE_QUERY.format(radius=radius, lat=latitude, lon=longitude)
        inland_query = const.INLAND_QUERY.format(radius=radius, lat=latitude, lon=longitude)
        last_error: Exception | None = None

        for endpoint in const.OVERPASS_ENDPOINTS:
            try:
                marine_response, inland_response = await asyncio.gather(
                    self.get(endpoint, params={"data": marine_query}),
                    self.get(endpoint, params={"data": inland_query}),
                )
                marine_response.raise_for_status()
                inland_response.raise_for_status()
                marine = utils.nearest_element(
                    latitude,
                    longitude,
                    marine_response.json().get("elements", []),
                    marine=True,
                )
                inland = utils.nearest_element(
                    latitude,
                    longitude,
                    inland_response.json().get("elements", []),
                    marine=False,
                )
                return {
                    "nearest_marine_km": marine[0] if marine else None,
                    "marine_feature": marine[1] if marine else None,
                    "nearest_inland_water_km": inland[0] if inland else None,
                    "inland_feature": inland[1] if inland else None,
                }
            except niquests.HTTPError as exc:
                last_error = exc
                _LOGGER.warning(
                    "overpass_request_failed",
                    endpoint=endpoint,
                    status=getattr(exc.response, "status_code", None),
                )
                continue

        if last_error is not None:
            raise last_error
        return {
            "nearest_marine_km": None,
            "marine_feature": None,
            "nearest_inland_water_km": None,
            "inland_feature": None,
        }
