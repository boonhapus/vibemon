"""Open-Meteo API constants for climate weather and air-quality fetches."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "open-meteo.weather_forecast"

WEATHER_API_BASE_URL: Final[str] = "https://api.open-meteo.com/"
AIR_QUALITY_API_BASE_URL: Final[str] = "https://air-quality-api.open-meteo.com/"

FORECAST_PATH: Final[str] = "/v1/forecast"
AIR_QUALITY_PATH: Final[str] = "/v1/air-quality"

TIMEZONE: Final[str] = "GMT"

# Default lookback when callers omit explicit start/end dates.
DEFAULT_LOOKBACK: Final[dt.timedelta] = dt.timedelta(days=1) + dt.timedelta(weeks=6)

# Daily forecast variables requested for climate synthesis.
DAILY_VARIABLES: Final[tuple[str, ...]] = (
    "uv_index_max",
    "weather_code",
    "shortwave_radiation_sum",
    "relative_humidity_2m_mean",
    "temperature_2m_max",
    "temperature_2m_min",
    "visibility_mean",
    "cloud_cover_mean",
    "precipitation_sum",
    "et0_fao_evapotranspiration",
    "dew_point_2m_mean",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "cape_mean",
    "snowfall_sum",
)

# Hourly air-quality variables merged onto the daily weather frame.
HOURLY_AIR_QUALITY_VARIABLES: Final[tuple[str, ...]] = ("pm2_5", "dust")
