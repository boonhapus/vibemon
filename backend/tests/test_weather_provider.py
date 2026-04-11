from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.engine.fallback import datetime_only_source
from app.providers.base import GenerationContext
from app.providers.weather import WeatherProvider, _map_temperature_votes


@pytest.mark.asyncio
async def test_temperature_vote_thresholds() -> None:
    assert _map_temperature_votes(-2.0)[0][0] == "Ice"
    assert _map_temperature_votes(10.0)[0][0] == "Water"
    assert _map_temperature_votes(20.0)[0][0] == "Grass"
    assert _map_temperature_votes(30.0)[0][0] == "Fire"
    assert _map_temperature_votes(40.0)[0][0] == "Ground"


@pytest.mark.asyncio
async def test_weather_open_meteo_mock() -> None:
    ctx = GenerationContext(
        user_id="t",
        timestamp=datetime(2024, 6, 1, 14, tzinfo=timezone.utc),
        latitude=51.5,
        longitude=-0.12,
        auth_tokens={},
    )
    fake_json = {
        "current": {
            "temperature_2m": 12.0,
            "wind_speed_10m": 40.0,
            "precipitation": 0.0,
            "relative_humidity_2m": 60.0,
            "uv_index": 2.0,
            "weather_code": 0,
        }
    }
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = MagicMock(return_value=fake_json)

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.get = AsyncMock(return_value=fake_resp)

    with patch("app.providers.weather.niquests.AsyncSession", return_value=fake_session):
        out = await WeatherProvider().fetch(ctx)

    assert out.speed_factor == pytest.approx(40 / 80.0)
    assert out.raw.get("weather_live") is True
    assert out.element_votes


@pytest.mark.asyncio
async def test_weather_api_failure_falls_back() -> None:
    ctx = GenerationContext(
        user_id="t",
        timestamp=datetime(2024, 6, 1, 14, tzinfo=timezone.utc),
        latitude=51.5,
        longitude=-0.12,
        auth_tokens={},
    )

    async def boom(*a: object, **k: object) -> None:
        raise ConnectionError("down")

    fake_session = MagicMock()
    fake_session.__aenter__ = AsyncMock(return_value=fake_session)
    fake_session.__aexit__ = AsyncMock(return_value=None)
    fake_session.get = boom

    with patch("app.providers.weather.niquests.AsyncSession", return_value=fake_session):
        out = await WeatherProvider().fetch(ctx)

    fb = datetime_only_source(ctx.timestamp, ctx.latitude)
    assert out.raw.get("weather_live") is False
    assert out.element_votes[0][0] == fb.element_votes[0][0]
