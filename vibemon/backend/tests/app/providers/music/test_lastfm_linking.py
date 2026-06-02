"""Tests for Last.fm web-auth linking helpers."""

import uuid

from app.providers.music.lastfm import linking


def test_build_authorize_url_includes_callback() -> None:
    trainer_id = uuid.UUID("019e64dd-7174-711f-8f6a-73b8997aec8e")
    url = linking.build_authorize_url(trainer_id, "pending-token")

    assert "api_key=test-api-key" in url
    assert "token=pending-token" in url
    assert "cb=http%3A%2F%2F127.0.0.1%3A8765%2Flastfm%2Fcallback" in url
    assert "trainer_id" not in url


def test_build_local_authorize_url() -> None:
    trainer_id = uuid.UUID("019e64dd-7174-711f-8f6a-73b8997aec8e")
    assert (
        linking.build_local_authorize_url(trainer_id)
        == "http://127.0.0.1:8765/lastfm/authorize?trainer_id=019e64dd-7174-711f-8f6a-73b8997aec8e"
    )
