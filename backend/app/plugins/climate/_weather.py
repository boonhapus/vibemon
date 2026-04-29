import datetime as dt

import niquests

from app.plugins import api_hooks
from app import __project__


class OpenMeteoAPIClient(niquests.AsyncSession):
    """
    Fetches current weather conditions from OpenMeteo.

    Further reading:
      https://open-meteo.com/en/docs
    """

    def __init__(self, **session_opts) -> None:
        super().__init__(
            base_url="https://api.open-meteo.com/",
            hooks=api_hooks.LoggingHook(provider="open-meteo.weather_forecast"),
            **session_opts,
        )

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
            # 4 COMPLETE WEEKS
            start_date = end_date - dt.timedelta(days=1) - dt.timedelta(weeks=4)

        assert isinstance(start_date, dt.date), "start_date must be provided."
        assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

        p = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": ",".join([
                "uv_index_max",
                "weather_code",
                "snowfall_sum",
                "rain_sum",
                "shortwave_radiation_sum",
                "relative_humidity_2m_mean",
                "temperature_2m_mean",
                "apparent_temperature_mean",
                "visibility_mean",
                "surface_pressure_mean",
                "dew_point_2m_mean",
                "wind_speed_10m_max",
                "wind_gusts_10m_max",
            ]),
            "timezone": "GMT",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        r = await self.get("/v1/forecast", params=p)

        return r
