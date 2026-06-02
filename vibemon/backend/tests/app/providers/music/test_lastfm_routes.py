"""Tests for local Last.fm linking routes."""

import uuid

from starlette.testclient import TestClient
import pytest

from app.providers.music.lastfm import linking, routes, tokens


@pytest.fixture
def client() -> TestClient:
    routes.reset_link_waiter()
    return TestClient(routes.create_app())


def test_finish_returns_400_without_auth_state(client: TestClient) -> None:
    response = client.get("/lastfm/finish")
    assert response.status_code == 400
    assert "Missing Last.fm auth state" in response.text


def test_finish_waits_when_session_not_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.UUID("019e64dd-7174-711f-8f6a-73b8997aec8e")
    token = "pending-token"
    state = linking.build_state(trainer_id, token)

    async def _pending(_token: str) -> tokens.LastFmSessionResponse | None:
        return None

    async def _noop_poll(_trainer_id: uuid.UUID, _token: str) -> None:
        return

    monkeypatch.setattr(tokens, "try_get_session", _pending)
    monkeypatch.setattr(routes, "_poll_until_linked", _noop_poll)

    client.cookies.set(routes._STATE_COOKIE, state)
    response = client.get("/lastfm/finish")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Waiting for Last.fm approval" in response.text


def test_finish_persists_when_session_ready(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.UUID("019e64dd-7174-711f-8f6a-73b8997aec8e")
    token = "pending-token"
    state = linking.build_state(trainer_id, token)
    session = tokens.LastFmSessionResponse(name="listener", key="session-key")
    message = f"Last.fm linked for trainer {trainer_id} as {session.name}."

    async def _ready(_token: str) -> tokens.LastFmSessionResponse | None:
        return session

    async def _noop_poll(_trainer_id: uuid.UUID, _token: str) -> None:
        return

    async def _persist(_trainer_id: uuid.UUID, _session: tokens.LastFmSessionResponse) -> str:
        return message

    monkeypatch.setattr(tokens, "try_get_session", _ready)
    monkeypatch.setattr(routes, "_poll_until_linked", _noop_poll)
    monkeypatch.setattr(routes, "_persist_lastfm_link", _persist)

    client.cookies.set(routes._STATE_COOKIE, state)
    response = client.get("/lastfm/finish")
    assert response.status_code == 200
    assert message in response.text
