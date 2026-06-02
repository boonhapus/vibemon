"""Tests for Open-Meteo HTTP response schemas."""

from typing import Any

import pydantic
import pytest

from app.providers.climate.openmeteo import schema as openmeteo_schema


def _sample_forecast_payload() -> dict[str, Any]:
    return {
        "latitude": 41.8781,
        "longitude": -87.6298,
        "elevation": 181.0,
        "generationtime_ms": 0.42,
        "timezone": "GMT",
        "daily": {
            "time": ["2026-05-18", "2026-05-19"],
            "uv_index_max": [6.2, 7.1],
            "weather_code": [3, 61],
            "shortwave_radiation_sum": [14.5, 12.0],
            "relative_humidity_2m_mean": [68.0, 72.0],
            "temperature_2m_max": [22.0, 19.5],
            "temperature_2m_min": [12.0, 11.0],
            "visibility_mean": [18000.0, 12000.0],
            "cloud_cover_mean": [55.0, 80.0],
            "precipitation_sum": [0.0, 4.2],
            "et0_fao_evapotranspiration": [3.1, 2.8],
            "dew_point_2m_mean": [8.0, 9.5],
            "wind_speed_10m_max": [18.0, 24.0],
            "wind_gusts_10m_max": [32.0, 45.0],
            "cape_mean": [120.0, 450.0],
            "snowfall_sum": [0.0, 0.0],
        },
    }


def _sample_air_quality_payload() -> dict[str, Any]:
    return {
        "latitude": 41.8781,
        "longitude": -87.6298,
        "hourly": {
            "time": [
                "2026-05-18T00:00",
                "2026-05-18T12:00",
                "2026-05-19T00:00",
                "2026-05-19T12:00",
            ],
            "pm2_5": [12.0, 18.0, 20.0, None],
            "dust": [4.0, 6.0, 8.0, 10.0],
        },
    }


def test_forecast_response_ignores_unknown_fields() -> None:
    parsed = openmeteo_schema.ForecastResponse.model_validate(_sample_forecast_payload())
    assert parsed.elevation == 181.0
    assert parsed.daily.weather_code == [3, 61]


def test_air_quality_response_parses_hourly_series() -> None:
    parsed = openmeteo_schema.AirQualityResponse.model_validate(_sample_air_quality_payload())
    assert parsed.hourly.pm2_5 == [12.0, 18.0, 20.0, None]
    assert parsed.hourly.dust[-1] == 10.0


def test_forecast_response_requires_daily_variables() -> None:
    payload = _sample_forecast_payload()
    del payload["daily"]["cape_mean"]
    with pytest.raises(pydantic.ValidationError):
        openmeteo_schema.ForecastResponse.model_validate(payload)
