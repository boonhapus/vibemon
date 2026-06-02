"""Open-Meteo HTTP response schemas for climate weather and air-quality fetches."""

import pydantic

from . import const


class _OpenMeteoModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="ignore")


class DailyFrame(_OpenMeteoModel):
    """Daily parallel arrays returned by the forecast endpoint."""

    time: list[str]
    uv_index_max: list[float | None]
    weather_code: list[int | None]
    shortwave_radiation_sum: list[float | None]
    relative_humidity_2m_mean: list[float | None]
    temperature_2m_max: list[float | None]
    temperature_2m_min: list[float | None]
    visibility_mean: list[float | None]
    cloud_cover_mean: list[float | None]
    precipitation_sum: list[float | None]
    et0_fao_evapotranspiration: list[float | None]
    dew_point_2m_mean: list[float | None]
    wind_speed_10m_max: list[float | None]
    wind_gusts_10m_max: list[float | None]
    cape_mean: list[float | None]
    snowfall_sum: list[float | None]


class ForecastResponse(_OpenMeteoModel):
    """Parsed payload from ``OpenMeteoClient.forecast``."""

    latitude: float
    longitude: float
    elevation: float
    daily: DailyFrame


class HourlyAirQualityFrame(_OpenMeteoModel):
    """Hourly parallel arrays returned by the air-quality endpoint."""

    time: list[str]
    pm2_5: list[float | None]
    dust: list[float | None]


class AirQualityResponse(_OpenMeteoModel):
    """Parsed payload from ``OpenMeteoClient.air_quality``."""

    latitude: float
    longitude: float
    hourly: HourlyAirQualityFrame


assert frozenset(DailyFrame.model_fields) - {"time"} == frozenset(const.DAILY_VARIABLES)
assert frozenset(HourlyAirQualityFrame.model_fields) - {"time"} == frozenset(const.HOURLY_AIR_QUALITY_VARIABLES)
