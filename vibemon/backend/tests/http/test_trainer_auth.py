"""HTTP trainer auth route tests."""

from collections.abc import AsyncGenerator
import io

from litestar import Litestar
from litestar.testing import AsyncTestClient
from PIL import Image
import pytest

from app.domains.sprite import types as sprite_types
from app.genai import vibemon_assets
from app.http.app import create_app
from app.http.deps import SESSION_COOKIE
from app.storage.blob.monstore import get_default_monstore


@pytest.fixture
def http_app() -> Litestar:
    return create_app()


@pytest.fixture
async def client(http_app: Litestar) -> AsyncGenerator[AsyncTestClient[Litestar]]:
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


def _png_bytes() -> bytes:
    payload = io.BytesIO()
    Image.new("RGB", (16, 16), "#ffffff").save(payload, format="PNG")
    return payload.getvalue()


async def test_check_username_available(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/api/trainers/check-username", json={"username": "NewTrainer"})
    assert response.status_code == 201
    assert response.json() == {"available": True, "detail": None}


async def test_check_username_taken(client: AsyncTestClient[Litestar]) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Taken"})
    assert register.status_code == 201

    response = await client.post("/api/trainers/check-username", json={"username": "taken"})
    assert response.status_code == 201
    assert response.json() == {
        "available": False,
        "detail": "That username is already taken.",
    }


async def test_check_username_rejects_invalid_name(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/api/trainers/check-username", json={"username": "a"})
    assert response.status_code == 422


async def test_register_creates_trainer_and_session(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/api/trainers/register", json={"username": "Ada"})
    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "ada"
    assert payload["crew_count"] == 0
    assert payload["reference_url"] is None
    assert payload["reference_selected_revision"] is None
    assert payload["reference_max_revision"] is None
    assert SESSION_COOKIE in response.cookies


async def test_register_rejects_duplicate_username(client: AsyncTestClient[Litestar]) -> None:
    first = await client.post("/api/trainers/register", json={"username": "Kai"})
    assert first.status_code == 201

    second = await client.post("/api/trainers/register", json={"username": "Kai"})
    assert second.status_code == 409


async def test_register_rejects_case_insensitive_duplicate(client: AsyncTestClient[Litestar]) -> None:
    first = await client.post("/api/trainers/register", json={"username": "Bahnoopus"})
    assert first.status_code == 201

    second = await client.post("/api/trainers/register", json={"username": "bahnoopus"})
    assert second.status_code == 409


async def test_login_existing_trainer(client: AsyncTestClient[Litestar]) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Nova"})
    assert register.status_code == 201
    trainer_id = register.json()["id"]
    client.cookies.clear()

    response = await client.post("/api/trainers/login", json={"username": "Nova"})
    assert response.status_code == 201
    assert response.json()["username"] == "nova"
    assert response.cookies[SESSION_COOKIE] == trainer_id


async def test_login_matches_case_insensitive_name(client: AsyncTestClient[Litestar]) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Bahnoopus"})
    assert register.status_code == 201
    client.cookies.clear()

    response = await client.post("/api/trainers/login", json={"username": "bahnoopus"})
    assert response.status_code == 201
    assert response.json()["username"] == "bahnoopus"


async def test_login_unknown_trainer_returns_404(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post("/api/trainers/login", json={"username": "Missing"})
    assert response.status_code == 404


async def test_me_requires_session(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/trainers/me")
    assert response.status_code == 401


async def test_me_returns_trainer_with_crew_count(client: AsyncTestClient[Litestar]) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Rae"})
    assert register.status_code == 201
    trainer_id = register.json()["id"]

    response = await client.get("/api/trainers/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": trainer_id,
        "username": "rae",
        "crew_count": 0,
        "reference_url": None,
        "reference_selected_revision": None,
        "reference_max_revision": None,
    }


async def test_logout_clears_session(client: AsyncTestClient[Litestar]) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Jun"})
    assert register.status_code == 201

    logout = await client.post("/api/trainers/logout")
    assert logout.status_code == 204

    me = await client.get("/api/trainers/me")
    assert me.status_code == 401


async def test_upload_trainer_reference_requires_session(client: AsyncTestClient[Litestar]) -> None:
    response = await client.post(
        "/api/trainers/reference",
        files={"image": ("trainer.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 401


async def test_upload_trainer_reference_generates_and_returns_url(
    client: AsyncTestClient[Litestar],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    register = await client.post("/api/trainers/register", json={"username": "Reference"})
    assert register.status_code == 201
    trainer_id = register.json()["id"]

    reference_png = _png_bytes()

    class _FakeGenerator:
        async def detect_trainer_reference_facing(
            self,
            reference_png: bytes,
        ) -> sprite_types.SpriteFacing:
            assert reference_png
            return sprite_types.SpriteFacing.RIGHT

        async def generate_trainer_reference(
            self,
            likeness_bytes: bytes,
            *,
            username: str,
            likeness_media_type: str,
        ) -> tuple[bytes, object]:
            assert likeness_bytes
            assert username == "reference"
            assert likeness_media_type == "image/png"
            from app.domains.vibemon.brand import CHROMA_KEY_CANDIDATES

            return reference_png, CHROMA_KEY_CANDIDATES[2]

    monkeypatch.setattr(vibemon_assets, "get_default_asset_generator", lambda: _FakeGenerator())
    get_default_monstore.cache_clear()

    response = await client.post(
        "/api/trainers/reference",
        files={"image": ("trainer.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["username"] == "reference"
    assert payload["reference_url"] == f"/api/assets/trainers/{trainer_id}/v1/r1/sprite/reference.png"
    assert payload["reference_selected_revision"] == 1
    assert payload["reference_max_revision"] == 1

    asset = await client.get(payload["reference_url"])
    assert asset.status_code == 200
    assert asset.content

    monstore = get_default_monstore()
    raw_key = f"trainers/{trainer_id}/v1/r1/sprite/reference-raw.png"
    assert await monstore.has(raw_key)
