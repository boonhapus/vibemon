from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.domain.context import SourceData
from app.domain.models import GenerateRequestBody
from app.services.generate_service import generate


def _weather_source() -> SourceData:
    return SourceData(
        hp_factor=0.5,
        attack_factor=0.55,
        defense_factor=0.55,
        speed_factor=0.3,
        element_votes=[("Grass", 0.5)],
        hue_primary=115.0,
        luminosity=0.55,
        flavour_text="17°C, clear sky near 40.7°, -74.0°",
        raw={
            "weather_live": True,
            "temperature_c": 17.0,
            "wind_kmh": 24.0,
            "precipitation_mm": 0.0,
            "relative_humidity_pct": 50.0,
            "uv_index": 3.0,
            "weather_code": 0,
        },
    )


def _spotify_source() -> SourceData:
    return SourceData(
        hp_factor=0.8,
        attack_factor=0.7,
        defense_factor=None,
        sp_attack_factor=0.6,
        sp_defense_factor=0.3,
        speed_factor=0.7,
        element_votes=[("Fire", 0.6), ("Electric", 0.7)],
        hue_primary=40.0,
        luminosity=0.55,
        flavour_text="Recent tracks: Heavy Metal Song, Chill Track, Pop Hit",
        raw={
            "spotify": True,
            "track_count": 30,
            "track_count_7d": 20,
            "unique_artists": 10,
            "avg_bpm": 140.0,
            "avg_listening_hour": 15.0,
            "genre_count": 5,
            "enrichment_tags": ["metal", "rock", "energetic"],
        },
    )


@pytest.mark.asyncio
async def test_weather_only_generation():
    request = GenerateRequestBody(
        user_id="test-weather-only",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={},
        render_assets="none",
    )
    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        result = await generate(request)

    assert "player" in result
    assert "enemy" in result
    player = result["player"]
    assert player["source"] == "weather"
    assert "Grass" in (player["stats"]["element"], player["stats"].get("element_secondary"))


@pytest.mark.asyncio
async def test_multi_provider_generates_different_stats():
    request_weather = GenerateRequestBody(
        user_id="test-compare",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={},
        render_assets="none",
    )
    request_multi = GenerateRequestBody(
        user_id="test-compare",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={"spotify": "fake-token"},
        render_assets="none",
    )

    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        result_weather = await generate(request_weather)

    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        with patch("app.infra.providers.spotify.SpotifyProvider.fetch", new_callable=AsyncMock) as mock_s:
            mock_s.return_value = _spotify_source()
            result_multi = await generate(request_multi)

    pw = result_weather["player"]
    pm = result_multi["player"]

    weather_stats = pw["stats"]
    multi_stats = pm["stats"]

    stat_keys = ["hp", "attack", "defense", "sp_attack", "sp_defense", "speed"]
    diffs = [abs(weather_stats[k] - multi_stats[k]) for k in stat_keys]
    assert any(d > 0 for d in diffs), "Multi-provider should produce different stats"


@pytest.mark.asyncio
async def test_multi_provider_source_label():
    request = GenerateRequestBody(
        user_id="test-source-label",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={"spotify": "fake-token"},
        render_assets="none",
    )

    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        with patch("app.infra.providers.spotify.SpotifyProvider.fetch", new_callable=AsyncMock) as mock_s:
            mock_s.return_value = _spotify_source()
            result = await generate(request)

    player = result["player"]
    assert "weather" in player["source"]
    assert "spotify" in player["source"]


@pytest.mark.asyncio
async def test_multi_provider_stat_origins_include_spotify():
    request = GenerateRequestBody(
        user_id="test-origins",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={"spotify": "fake-token"},
        render_assets="none",
    )

    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        with patch("app.infra.providers.spotify.SpotifyProvider.fetch", new_callable=AsyncMock) as mock_s:
            mock_s.return_value = _spotify_source()
            result = await generate(request)

    origins = result["player"]["stat_origins"]
    spotify_mentioned = any("Spotify" in v for v in origins.values())
    assert spotify_mentioned, f"stat_origins should mention Spotify: {origins}"


@pytest.mark.asyncio
async def test_spotify_failure_falls_back_to_weather():
    request = GenerateRequestBody(
        user_id="test-spotify-fail",
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={"spotify": "bad-token"},
        render_assets="none",
    )

    with patch("app.infra.providers.weather.WeatherProvider.fetch", new_callable=AsyncMock) as mock_w:
        mock_w.return_value = _weather_source()
        with patch("app.infra.providers.spotify.SpotifyProvider.fetch", new_callable=AsyncMock) as mock_s:
            mock_s.side_effect = Exception("API error")
            result = await generate(request)

    player = result["player"]
    assert player["source"] == "weather"
