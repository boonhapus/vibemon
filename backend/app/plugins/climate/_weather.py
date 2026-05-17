from collections.abc import Awaitable, Callable
from typing import Any, cast
from urllib.parse import urlparse, urlunparse
import datetime as dt
import os

from niquests.adapters import AsyncHTTPAdapter
import niquests

from app import __project__
from app.plugins.api_hooks import LoggingHook, RateLimiterHook


class OpenMeteoAdapter(AsyncHTTPAdapter):
    """Rewrites placeholder URLs to real Open Meteo subdomains."""

    def __init__(self, subdomain: str, *a: Any, **kw: Any) -> None:
        self.subdomain = subdomain
        super().__init__(*a, **kw)

    async def send(
        self,
        request: niquests.PreparedRequest,
        stream: bool = False,
        timeout: Any = None,
        verify: bool | str | bytes | os.PathLike[str] = True,
        cert: str | tuple[str, str] | tuple[str, str, str] | None = None,
        proxies: dict[str, str] | None = None,
        on_post_connection: Callable[[Any], Awaitable[None]] | None = None,
        on_upload_body: Callable[[int, int | None, bool, bool], Awaitable[None]] | None = None,
        on_early_response: Callable[[niquests.Response], Awaitable[None]] | None = None,
        multiplexed: bool = False,
    ) -> niquests.AsyncResponse:
        if request.url is None:
            raise ValueError("Prepared request URL was not set")

        parts = urlparse(request.url)
        rewritten = urlunparse(parts._replace(netloc=f"{self.subdomain}.open-meteo.com"))
        request.url = rewritten.decode("utf-8") if isinstance(rewritten, bytes) else rewritten

        return await super().send(
            request,
            stream=stream,
            timeout=timeout,
            verify=verify,
            cert=cert,
            proxies=proxies,
            on_post_connection=on_post_connection,
            on_upload_body=on_upload_body,
            on_early_response=on_early_response,
            multiplexed=multiplexed,
        )


class OpenMeteoAPIClient(niquests.AsyncSession):
    """
    Fetches current weather conditions from OpenMeteo.

    Further reading:
      https://open-meteo.com/en/docs
    """

    provider_name = "open-meteo.weather_forecast"

    def __init__(self, **session_opts: Any) -> None:
        # fmt: off
        RATE_LIMITER = RateLimiterHook(
            (    600, dt.timedelta(minutes= 1)),
            (  5_000, dt.timedelta(hours  = 1)),
            ( 10_000, dt.timedelta(days   = 1)),
            (300_000, dt.timedelta(days   =30)),
            provider=OpenMeteoAPIClient.provider_name,
        )
        # fmt: on
        RETRY_POLICY = niquests.RetryConfiguration(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503],
            allowed_methods=["GET"],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        hooks = cast(Any, LoggingHook(provider=OpenMeteoAPIClient.provider_name) + RATE_LIMITER)
        super().__init__(
            base_url="https://api.open-meteo.com/",
            hooks=hooks,
            retries=RETRY_POLICY,
            **session_opts,
        )

        self.mount("https://__weather__", adapter=OpenMeteoAdapter("api"))
        self.mount("https://__air_quality__", adapter=OpenMeteoAdapter("air-quality-api"))

        self.headers.update(
            {
                "user-agent": f"{__project__.__name__} v{__project__.__version__} (+github/{__project__.__slug__})",
                "content-type": "application/json",
                "accept": "application/json",
            }
        )

    async def current_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> niquests.Response:
        """Find the weather at a given coordinate."""
        if end_date is None:
            end_date = dt.datetime.now(tz=dt.UTC).date()

        assert isinstance(end_date, dt.date), "end_date must be provided."

        if start_date is None:
            # 6 COMPLETE WEEKS
            start_date = end_date - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        assert isinstance(start_date, dt.date), "start_date must be provided."
        assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

        p: dict[str, str] = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "daily": ",".join(
                [
                    "uv_index_max",
                    "weather_code",
                    "shortwave_radiation_sum",
                    "relative_humidity_2m_mean",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "apparent_temperature_mean",
                    "visibility_mean",
                    "pressure_msl_mean",
                    "pressure_msl_max",
                    "pressure_msl_min",
                    "cloud_cover_mean",
                    "precipitation_sum",
                    "et0_fao_evapotranspiration",
                    "dew_point_2m_mean",
                    "wind_speed_10m_max",
                    "wind_gusts_10m_max",
                    "cape_mean",
                    "snowfall_sum",
                ]
            ),
            "hourly": "soil_moisture_0_to_1cm",
            "timezone": "GMT",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get("https://__weather__/v1/forecast", params=p)

        return r

    async def air_quality(
        self,
        latitude: float,
        longitude: float,
        start_date: dt.date | None = None,
        end_date: dt.date | None = None,
    ) -> niquests.Response:
        """Fetch air quality data (PM2.5) for Poison type mapping."""
        if end_date is None:
            end_date = dt.datetime.now(tz=dt.UTC).date()

        assert isinstance(end_date, dt.date), "end_date must be provided."

        if start_date is None:
            start_date = end_date - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        assert isinstance(start_date, dt.date), "start_date must be provided."
        assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

        p: dict[str, str] = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "hourly": "pm2_5,dust",
            "timezone": "GMT",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get("https://__air_quality__/v1/air-quality", params=p)

        return r
