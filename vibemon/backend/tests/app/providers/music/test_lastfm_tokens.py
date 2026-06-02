"""Tests for Last.fm auth token helpers."""

import pytest

from app.providers.music.lastfm import tokens


@pytest.mark.asyncio
async def test_try_get_session_returns_none_for_pending_token(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise_pending(_token: str) -> tokens.LastFmSessionResponse:
        raise tokens.LastFmApiError(14, "This token has not been authorized")

    monkeypatch.setattr(tokens, "get_session", _raise_pending)
    assert await tokens.try_get_session("pending") is None


@pytest.mark.asyncio
async def test_try_get_session_reraises_other_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _raise_invalid(_token: str) -> tokens.LastFmSessionResponse:
        raise tokens.LastFmApiError(9, "Invalid session key")

    monkeypatch.setattr(tokens, "get_session", _raise_invalid)
    with pytest.raises(tokens.LastFmApiError, match="Invalid session key"):
        await tokens.try_get_session("bad")
