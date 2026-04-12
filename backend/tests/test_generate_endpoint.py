from __future__ import annotations

from litestar.status_codes import HTTP_422_UNPROCESSABLE_ENTITY
from litestar.testing import TestClient

from app.main import create_app


def make_client() -> TestClient:
    return TestClient(app=create_app())


def test_health_ok() -> None:
    with make_client() as c:
        r = c.get("/api/v1/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "providers" in body


def test_generate_missing_location_422() -> None:
    with make_client() as c:
        r = c.post("/api/v1/generate", json={"user_id": "x"})
        assert r.status_code == HTTP_422_UNPROCESSABLE_ENTITY


def test_generate_returns_player_and_enemy() -> None:
    with make_client() as c:
        r = c.post(
            "/api/v1/generate",
            json={
                "user_id": "test",
                "latitude": 51.5,
                "longitude": -0.1,
                "auth_tokens": {},
                "render_assets": "none",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "player" in data and "enemy" in data
        p = data["player"]
        assert p["uid"] == "test"
        assert "stats" in p and "moves" in p and "visual_dna" in p
        e = data["enemy"]
        assert e["uid"].startswith("enemy_")
        assert len(e["moves"]) == 4
