"""Tests for the Last.fm Web API client."""

from app.providers.music.lastfm.api import LastFmAPIClient


def test_lastfm_client_uses_provider_name() -> None:
    client = LastFmAPIClient("test-api-key")
    assert client.provider_name == "lastfm.web_api"
