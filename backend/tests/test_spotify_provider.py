from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

import pytest

from app.providers.base import GenerationContext, SourceData
from app.providers.spotify import (
    SpotifyProvider,
    derive_hue,
    _normalize_bpm,
    _normalize_track_count,
    _normalize_genre_count,
    _extract_tracks,
    _count_recent_7d,
    _average_listening_hour,
    _deduplicate_tracks,
    _classify_tags,
)


def _make_context(token: str = "test-token") -> GenerationContext:
    return GenerationContext(
        user_id="test-user",
        timestamp=datetime(2026, 4, 11, 14, 0, 0, tzinfo=timezone.utc),
        latitude=40.7,
        longitude=-74.0,
        auth_tokens={"spotify": token} if token else {},
    )


def _make_spotify_item(
    track_name: str = "Test Track",
    artist_name: str = "Test Artist",
    played_at: str = "2026-04-10T12:00:00Z",
) -> dict[str, Any]:
    return {
        "track": {
            "name": track_name,
            "artists": [{"name": artist_name}],
            "album": {"name": "Test Album"},
        },
        "played_at": played_at,
    }


class TestNormalisationFunctions:
    def test_normalize_bpm_low(self):
        assert _normalize_bpm(60) == 0.0

    def test_normalize_bpm_high(self):
        assert _normalize_bpm(180) == 1.0

    def test_normalize_bpm_mid(self):
        assert 0.4 < _normalize_bpm(120) < 0.6

    def test_normalize_bpm_clamp(self):
        assert _normalize_bpm(30) == 0.0
        assert _normalize_bpm(250) == 1.0

    def test_normalize_track_count(self):
        assert _normalize_track_count(1) == 0.0
        assert _normalize_track_count(50) == 1.0
        assert 0.0 < _normalize_track_count(25) < 1.0

    def test_normalize_genre_count(self):
        assert _normalize_genre_count(1) == 0.0
        assert _normalize_genre_count(10) == 1.0


class TestDeriveHue:
    def test_high_energy_high_valence(self):
        hue = derive_hue(1.0, 1.0)
        assert 0 <= hue < 360

    def test_low_energy_low_valence(self):
        hue = derive_hue(0.0, 0.0)
        assert 200 <= hue <= 280

    def test_deterministic(self):
        assert derive_hue(0.5, 0.5) == derive_hue(0.5, 0.5)


class TestExtractTracks:
    def test_basic_extraction(self):
        items = [_make_spotify_item("Song A", "Artist A")]
        tracks = _extract_tracks(items)
        assert len(tracks) == 1
        assert tracks[0]["name"] == "Song A"
        assert tracks[0]["artist"] == "Artist A"

    def test_empty_items(self):
        assert _extract_tracks([]) == []

    def test_missing_track_field(self):
        items = [{"played_at": "2026-04-10T12:00:00Z"}]
        assert _extract_tracks(items) == []


class TestCountRecent7d:
    def test_counts_within_window(self):
        now = datetime(2026, 4, 11, 14, 0, 0, tzinfo=timezone.utc)
        tracks = [
            {"played_at": "2026-04-10T12:00:00Z"},
            {"played_at": "2026-04-05T12:00:00Z"},
            {"played_at": "2026-04-01T12:00:00Z"},
        ]
        count = _count_recent_7d(tracks, now)
        assert count == 2

    def test_empty_tracks(self):
        now = datetime(2026, 4, 11, 14, 0, 0, tzinfo=timezone.utc)
        assert _count_recent_7d([], now) == 0


class TestAverageListeningHour:
    def test_basic_average(self):
        tracks = [
            {"played_at": "2026-04-10T14:00:00Z"},
            {"played_at": "2026-04-10T16:00:00Z"},
        ]
        avg = _average_listening_hour(tracks)
        assert 14.5 < avg < 15.5

    def test_empty(self):
        assert _average_listening_hour([]) == 12.0


class TestDeduplicateTracks:
    def test_removes_duplicates(self):
        tracks = [
            {"name": "Song", "artist": "Art"},
            {"name": "song", "artist": "art"},
            {"name": "Other", "artist": "Art"},
        ]
        unique = _deduplicate_tracks(tracks)
        assert len(unique) == 2


class TestClassifyTags:
    def test_classification(self):
        tags = ["energetic", "dark", "chill", "aggressive", "pop"]
        result = _classify_tags(tags)
        assert result["energetic"] == 1
        assert result["dark"] == 1
        assert result["chill"] == 1
        assert result["aggressive"] == 1

    def test_empty_tags(self):
        result = _classify_tags([])
        assert all(v == 0 for v in result.values())


class TestSpotifyProvider:
    def test_source_id(self):
        p = SpotifyProvider()
        assert p.source_id == "spotify"

    @pytest.mark.asyncio
    async def test_no_token_raises(self):
        ctx = _make_context(token="")
        ctx.auth_tokens = {}
        p = SpotifyProvider()
        with pytest.raises(ValueError, match="No Spotify token"):
            await p.fetch(ctx)

    @pytest.mark.asyncio
    async def test_fetch_with_mock_data(self):
        items = [
            _make_spotify_item("Heavy Metal Song", "Metal Band", "2026-04-10T23:00:00Z"),
            _make_spotify_item("Chill Track", "Ambient Artist", "2026-04-09T14:00:00Z"),
            _make_spotify_item("Pop Hit", "Pop Star", "2026-04-08T10:00:00Z"),
        ]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {"tags": ["metal", "aggressive"], "bpm": 150}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        assert isinstance(result, SourceData)
        assert result.raw.get("spotify") is True
        assert result.raw["track_count"] == 3
        assert result.hp_factor is not None
        assert result.speed_factor is not None
        assert result.flavour_text is not None

    @pytest.mark.asyncio
    async def test_musicbrainz_fallback_to_lastfm(self):
        items = [_make_spotify_item("Test", "Artist", "2026-04-10T12:00:00Z")]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {"tags": ["chill", "acoustic"]}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        assert isinstance(result, SourceData)
        assert any(e == "Water" for e, _ in result.element_votes)

    @pytest.mark.asyncio
    async def test_both_enrichment_fail_still_returns_data(self):
        items = [
            _make_spotify_item("Song", "Artist", "2026-04-10T12:00:00Z"),
            _make_spotify_item("Song2", "Artist2", "2026-04-09T15:00:00Z"),
        ]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        assert isinstance(result, SourceData)
        assert result.hp_factor is not None
        assert result.speed_factor is not None
        assert result.raw["track_count"] == 2

    @pytest.mark.asyncio
    async def test_no_recent_tracks(self):
        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []

            ctx = _make_context()
            p = SpotifyProvider()
            result = await p.fetch(ctx)

        assert isinstance(result, SourceData)
        assert result.raw["track_count"] == 0

    @pytest.mark.asyncio
    async def test_night_listener_dark_vote(self):
        items = [
            _make_spotify_item("Song", "Artist", "2026-04-10T23:00:00Z"),
            _make_spotify_item("Song2", "Artist", "2026-04-10T23:30:00Z"),
            _make_spotify_item("Song3", "Artist", "2026-04-10T22:30:00Z"),
        ]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        dark_votes = [w for e, w in result.element_votes if e == "Dark"]
        assert len(dark_votes) > 0

    @pytest.mark.asyncio
    async def test_stat_factors_from_genre_intensity(self):
        items = [_make_spotify_item("Metal Song", "Metal Band", "2026-04-10T12:00:00Z")]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {"tags": ["metal", "hardcore", "aggressive"], "bpm": 160}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        assert result.attack_factor is not None
        assert result.attack_factor > 0.4

    @pytest.mark.asyncio
    async def test_calm_genres_boost_sp_defense(self):
        items = [_make_spotify_item("Calm Song", "Ambient Artist", "2026-04-10T12:00:00Z")]

        with patch("app.providers.spotify._fetch_spotify_recent", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = items
            with patch("app.providers.spotify._query_musicbrainz", new_callable=AsyncMock) as mock_mb:
                mock_mb.return_value = {"tags": ["classical", "ambient"]}
                with patch("app.providers.spotify._query_lastfm", new_callable=AsyncMock) as mock_lfm:
                    mock_lfm.return_value = {}

                    ctx = _make_context()
                    p = SpotifyProvider()
                    result = await p.fetch(ctx)

        assert result.sp_defense_factor is not None
        assert result.sp_defense_factor > 0.4
