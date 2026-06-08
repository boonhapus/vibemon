"""HTTP trainer auth route tests."""

from litestar.testing import AsyncTestClient
import pytest

from app.http.app import create_app
from app.http.deps import SESSION_COOKIE


@pytest.fixture
def http_app():
    return create_app()


@pytest.fixture
async def client(http_app):
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


async def test_check_username_available(client: AsyncTestClient) -> None:
    response = await client.post("/api/trainers/check-username", json={"username": "NewTrainer"})
    assert response.status_code == 201
    assert response.json() == {"available": True, "detail": None}


async def test_check_username_taken(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Taken"})
    assert register.status_code == 201

    response = await client.post("/api/trainers/check-username", json={"username": "taken"})
    assert response.status_code == 201
    assert response.json() == {
        "available": False,
        "detail": "That username is already taken.",
    }


async def test_check_username_rejects_invalid_name(client: AsyncTestClient) -> None:
    response = await client.post("/api/trainers/check-username", json={"username": "a"})
    assert response.status_code == 422


async def test_register_creates_trainer_and_session(client: AsyncTestClient) -> None:
    response = await client.post("/api/trainers/register", json={"username": "Ada"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "ada"
    assert payload["crew_count"] == 0
    assert SESSION_COOKIE in response.cookies


async def test_register_rejects_duplicate_username(client: AsyncTestClient) -> None:
    first = await client.post("/api/trainers/register", json={"username": "Kai"})
    assert first.status_code == 201

    second = await client.post("/api/trainers/register", json={"username": "Kai"})
    assert second.status_code == 409


async def test_register_rejects_case_insensitive_duplicate(client: AsyncTestClient) -> None:
    first = await client.post("/api/trainers/register", json={"username": "Bahnoopus"})
    assert first.status_code == 201

    second = await client.post("/api/trainers/register", json={"username": "bahnoopus"})
    assert second.status_code == 409


async def test_login_existing_trainer(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Nova"})
    assert register.status_code == 201
    trainer_id = register.json()["id"]
    client.cookies.clear()

    response = await client.post("/api/trainers/login", json={"username": "Nova"})
    assert response.status_code == 201
    assert response.json()["username"] == "nova"
    assert response.cookies[SESSION_COOKIE] == trainer_id


async def test_login_matches_case_insensitive_name(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Bahnoopus"})
    assert register.status_code == 201
    client.cookies.clear()

    response = await client.post("/api/trainers/login", json={"username": "bahnoopus"})
    assert response.status_code == 201
    assert response.json()["username"] == "bahnoopus"


async def test_login_unknown_trainer_returns_404(client: AsyncTestClient) -> None:
    response = await client.post("/api/trainers/login", json={"username": "Missing"})
    assert response.status_code == 404


async def test_me_requires_session(client: AsyncTestClient) -> None:
    response = await client.get("/api/trainers/me")
    assert response.status_code == 401


async def test_me_returns_trainer_with_crew_count(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Rae"})
    assert register.status_code == 201
    trainer_id = register.json()["id"]

    response = await client.get("/api/trainers/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": trainer_id,
        "username": "rae",
        "crew_count": 0,
    }


async def test_logout_clears_session(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Jun"})
    assert register.status_code == 201

    logout = await client.post("/api/trainers/logout")
    assert logout.status_code == 204

    me = await client.get("/api/trainers/me")
    assert me.status_code == 401


async def test_upload_trainer_portrait_accepts_image(client: AsyncTestClient) -> None:
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00" * 128
    response = await client.post(
        "/api/trainers/portrait",
        files={"image": ("trainer.png", payload, "image/png")},
    )
    assert response.status_code == 204
