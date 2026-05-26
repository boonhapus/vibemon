from typing import Any
import datetime as dt

import niquests

from app import __project__
from app.providers.api_hooks import LoggingHook, RateLimiterHook, provider_retry_policy

from . import const, utils


class OpenMeteoClient(niquests.AsyncSession):
    """
    Fetches weather and air-quality time series from Open-Meteo.

    Further reading:
      https://open-meteo.com/en/docs
    """

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = RateLimiterHook(
            (600, dt.timedelta(minutes=1)),
            (5_000, dt.timedelta(hours=1)),
            (10_000, dt.timedelta(days=1)),
            (300_000, dt.timedelta(days=30)),
            provider=OpenMeteoClient.provider_name,
        )
        super().__init__(
            base_url=const.WEATHER_API_BASE_URL,
            hooks=LoggingHook(provider=OpenMeteoClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            **session_opts,
        )
        self.headers.update(
            {
                "user-agent": f"{__project__.__name__} v{__project__.__version__} (+github/{__project__.__slug__})",
                "content-type": "application/json",
                "accept": "application/json",
            }
        )

    async def forecast(
        self,
        latitude: float,
        longitude: float,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> niquests.Response:
        """Fetch daily weather forecast for a coordinate."""
        start_date, end_date = utils.resolve_date_range(start_date=start_date, end_date=end_date)

        p: dict[str, str] = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "daily": ",".join(const.DAILY_VARIABLES),
            "timezone": const.TIMEZONE,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get(const.FORECAST_PATH, params=p)
        return r

    async def air_quality(
        self,
        latitude: float,
        longitude: float,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> niquests.Response:
        """Fetch hourly air-quality data for a coordinate."""
        start_date, end_date = utils.resolve_date_range(start_date=start_date, end_date=end_date)

        p: dict[str, str] = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "hourly": ",".join(const.HOURLY_AIR_QUALITY_VARIABLES),
            "timezone": const.TIMEZONE,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get(f"{const.AIR_QUALITY_API_BASE_URL.rstrip('/')}{const.AIR_QUALITY_PATH}", params=p)
        return r
