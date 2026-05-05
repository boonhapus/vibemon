import datetime as dt

from urllib.parse import urlparse, urlunparse
from niquests.adapters import AsyncHTTPAdapter
import niquests

from app.plugins.api_hooks import LoggingHook, RateLimiterHook
from app import __project__


class OpenMeteoAdapter(AsyncHTTPAdapter):
    """Rewrites placeholder URLs to real Open Meteo subdomains."""
    def __init__(self, subdomain: str, *a, **kw) -> None:
        self.subdomain = subdomain
        super().__init__(*a, **kw)

    async def send(self, request: niquests.PreapredRequest, **kwargs) -> niquests.AsyncResponse:
        parts = urlparse(request.url)
        request.url = urlunparse(parts._replace(netloc=f"{self.subdomain}.open-meteo.com"))
        return await super().send(request, **kwargs)


class OpenMeteoAPIClient(niquests.AsyncSession):
    """
    Fetches current weather conditions from OpenMeteo.

    Further reading:
      https://open-meteo.com/en/docs
    """
    provider_name = "open-meteo.weather_forecast"

    def __init__(self, **session_opts) -> None:
        RATE_LIMITER = RateLimiterHook(
            (    600, dt.timedelta(minutes= 1)),
            (  5_000, dt.timedelta(hours  = 1)),
            ( 10_000, dt.timedelta(days   = 1)),
            (300_000, dt.timedelta(days   =30)),
            provider=OpenMeteoAPIClient.provider_name,
        )
        RETRY_POLICY = niquests.RetryConfiguration(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503],
            allowed_methods=["GET"],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        super().__init__(
            base_url="https://api.open-meteo.com/",
            hooks=LoggingHook(provider=OpenMeteoAPIClient.provider_name) + RATE_LIMITER,
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
            end_date = dt.datetime.now(tz=dt.timezone.utc).date()
        
        assert isinstance(end_date, dt.date), "end_date must be provided."

        if start_date is None:
            # 6 COMPLETE WEEKS
            start_date = end_date - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        assert isinstance(start_date, dt.date), "start_date must be provided."
        assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

        p = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join([
                "uv_index_max",
                "weather_code",
                "shortwave_radiation_sum",
                "relative_humidity_2m_mean",
                "temperature_2m_max",
                "temperature_2m_min",
                "apparent_temperature_mean",
                "visibility_mean",
                "pressure_msl_mean",
                "cloud_cover_mean",
                "precipitation_sum",
                "et0_fao_evapotranspiration",
                "dew_point_2m_mean",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
                "cape_mean",
                "snowfall_sum",
            ]),
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
            end_date = dt.datetime.now(tz=dt.timezone.utc).date()

        assert isinstance(end_date, dt.date), "end_date must be provided."

        if start_date is None:
            start_date = end_date - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        assert isinstance(start_date, dt.date), "start_date must be provided."
        assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

        from collections.abc import Mapping

        p = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm2_5",
            "timezone": "GMT",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get("https://__air_quality__/v1/air-quality", params=p)

        return r
