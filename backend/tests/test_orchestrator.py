from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.engine.models import GenerateRequestBody
from app.engine.orchestrator import _build_stat_origins, _provider_active, generate
from app.providers.base import GenerationContext, SourceData, VibemonProvider
from app.providers.weather import WeatherProvider

_TS = datetime(2024, 6, 15, 14, 0, 0, tzinfo=timezone.utc)


def _ctx(**kw: object) -> GenerationContext:
    return GenerationContext(
        user_id=str(kw.get("user_id", "u")),
        timestamp=_TS,
        latitude=float(kw.get("latitude", 51.5)),
        longitude=float(kw.get("longitude", -0.1)),
        auth_tokens=dict(kw.get("auth_tokens", {})),  # type: ignore[arg-type]
    )


def _live_source() -> SourceData:
    return SourceData(
        hp_factor=0.6,
        attack_factor=0.55,
        defense_factor=0.55,
        speed_factor=0.5,
        element_votes=[("Fire", 0.7)],
        hue_primary=20.0,
        raw={
            "weather_live": True,
            "relative_humidity_pct": 60.0,
            "wind_kmh": 40.0,
            "uv_index": 3.0,
            "precipitation_mm": 0.0,
        },
    )


# --- _provider_active ---

def test_weather_always_active() -> None:
    assert _provider_active(WeatherProvider(), _ctx()) is True


def test_non_weather_requires_token() -> None:
    class FakeProvider(VibemonProvider):
        @property
        def source_id(self) -> str:
            return "spotify"

        async def fetch(self, context: GenerationContext) -> SourceData:  # pragma: no cover
            return SourceData()

    assert _provider_active(FakeProvider(), _ctx()) is False
    assert _provider_active(FakeProvider(), _ctx(auth_tokens={"spotify": "tok"})) is True


# --- _build_stat_origins ---

def test_stat_origins_live_weather() -> None:
    src = _live_source()
    o = _build_stat_origins(src)
    assert "Weather" in o["hp"]
    assert "Weather" in o["speed"]
    assert "Weather" in o["attack"]
    assert "Weather" in o["defense"]


def test_stat_origins_uv_boost_reflected() -> None:
    src = _live_source()
    src.raw["uv_index"] = 9.0
    o = _build_stat_origins(src)
    assert "UV" in o["attack"] or "uv" in o["attack"].lower() or "boost" in o["attack"].lower()


def test_stat_origins_fallback() -> None:
    src = SourceData(raw={"weather_live": False})
    o = _build_stat_origins(src)
    assert "fallback" in o["hp"].lower()
    assert "fallback" in o["speed"].lower()


# --- enemy UID ---

def test_enemy_uid_is_deterministic() -> None:
    ts = datetime(2024, 6, 15, 14, tzinfo=timezone.utc)
    lat, lon = 51.5, -0.1
    uid_a = f"enemy_{ts.strftime('%Y%m%d%H')}_{round(lat, 1)}_{round(lon, 1)}"
    uid_b = f"enemy_{ts.strftime('%Y%m%d%H')}_{round(lat, 1)}_{round(lon, 1)}"
    assert uid_a == uid_b


def test_enemy_uid_changes_with_hour() -> None:
    t1 = datetime(2024, 6, 15, 14, tzinfo=timezone.utc)
    t2 = datetime(2024, 6, 15, 15, tzinfo=timezone.utc)
    lat, lon = 51.5, -0.1
    uid1 = f"enemy_{t1.strftime('%Y%m%d%H')}_{round(lat, 1)}_{round(lon, 1)}"
    uid2 = f"enemy_{t2.strftime('%Y%m%d%H')}_{round(lat, 1)}_{round(lon, 1)}"
    assert uid1 != uid2


# --- full generate ---

@pytest.mark.asyncio
async def test_generate_returns_both_payloads() -> None:
    live = _live_source()
    with patch("app.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock, return_value=live):
        req = GenerateRequestBody(user_id="u1", latitude=51.5, longitude=-0.1)
        result = await generate(req)

    assert set(result) == {"player", "enemy"}
    p = result["player"]
    assert p["uid"] == "u1"
    assert p["fallback"] is False
    assert len(p["moves"]) == 4
    assert result["enemy"]["uid"].startswith("enemy_")


@pytest.mark.asyncio
async def test_generate_enemy_bst_within_band() -> None:
    """Enemy BST must be within ±15% of player BST after scaling."""
    live = _live_source()
    with patch("app.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock, return_value=live):
        req = GenerateRequestBody(user_id="bst-test", latitude=51.5, longitude=-0.1)
        result = await generate(req)

    def bst(s: dict) -> int:
        return s["hp"] + s["attack"] + s["defense"] + s["sp_attack"] + s["sp_defense"] + s["speed"]

    p_bst = bst(result["player"]["stats"])
    e_bst = bst(result["enemy"]["stats"])
    assert e_bst >= p_bst * 0.85 - 6  # small tolerance for per-stat int rounding
    assert e_bst <= p_bst * 1.15 + 6


@pytest.mark.asyncio
async def test_generate_provider_exception_skipped() -> None:
    """A provider raising inside asyncio.gather must not crash generate."""

    class BoomProvider(VibemonProvider):
        @property
        def source_id(self) -> str:
            return "boom"

        async def fetch(self, context: GenerationContext) -> SourceData:
            raise RuntimeError("intentional")

    live = _live_source()
    with (
        patch("app.engine.orchestrator.PROVIDER_REGISTRY", [WeatherProvider, BoomProvider]),
        patch("app.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock, return_value=live),
    ):
        req = GenerateRequestBody(user_id="u2", latitude=51.5, longitude=-0.1)
        result = await generate(req)

    assert "player" in result


@pytest.mark.asyncio
async def test_generate_fallback_flag_when_weather_unavailable() -> None:
    """If WeatherProvider returns a fallback source, player.fallback must be True."""
    from app.engine.fallback import datetime_only_source

    fallback_src = datetime_only_source(_TS, 51.5)
    with patch("app.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock, return_value=fallback_src):
        req = GenerateRequestBody(user_id="u3", latitude=51.5, longitude=-0.1)
        result = await generate(req)

    assert result["player"]["fallback"] is True
