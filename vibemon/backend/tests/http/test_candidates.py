"""HTTP tests for candidate generation and review routes."""

import io

from litestar.testing import AsyncTestClient
from PIL import Image
import pytest

from app.core.errors import InterfaceErrorCode
from app.domains.trainer import credits
from app.genai import vibemon_assets as genai_assets
from app.http.app import create_app
from app.storage.blob.monstore import get_default_monstore
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.fixture
def http_app():
    return create_app()


@pytest.fixture
async def client(http_app):
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


def _png_bytes() -> bytes:
    payload = io.BytesIO()
    Image.new("RGB", (16, 16), "#ffffff").save(payload, format="PNG")
    return payload.getvalue()


class _FakeAssetGenerator:
    facing_calls = 0

    async def detect_trainer_reference_facing(self, reference_png: bytes):
        from app.domains.sprite import types as sprite_types

        type(self).facing_calls += 1
        assert reference_png
        return sprite_types.SpriteFacing.RIGHT

    async def detect_vibemon_reference_facing(self, reference_png: bytes, *, vibemon_name: str):
        from app.domains.sprite import types as sprite_types

        type(self).facing_calls += 1
        assert reference_png
        return sprite_types.SpriteFacing.RIGHT

    async def generate_name(self, identity, moves, visual_notes):
        return "Testling"

    async def generate_reference_image(self, vibemon):
        return _png_bytes()

    async def generate_battle_cry_audio(self, vibemon):
        return b"mp3"

    async def generate_sprite_sheet_image(self, vibemon, reference_image: bytes):
        return _png_bytes()


@pytest.fixture(autouse=True)
def fake_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    _FakeAssetGenerator.facing_calls = 0
    monkeypatch.setattr(genai_assets, "get_default_asset_generator", lambda: _FakeAssetGenerator())
    get_default_monstore.cache_clear()


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.providers.registry.build_provider_instances",
        lambda provider_names=None: [FakeProvider()],
    )


async def _register(client: AsyncTestClient, username: str = "Hatcher") -> str:
    response = await client.post("/api/trainers/register", json={"username": username})
    assert response.status_code == 201
    return response.json()["id"]


async def test_generate_candidate_requires_session(client: AsyncTestClient) -> None:
    response = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert response.status_code == 401


async def test_generate_and_adopt_candidate(client: AsyncTestClient) -> None:
    trainer_id = await _register(client)

    generated = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert generated.status_code == 201
    payload = generated.json()
    assert payload["crew_count"] == 0
    candidate = payload["candidate"]
    assert candidate["name"] == "Testling"
    assert candidate["bst"] > 0
    assert candidate["reference_facing"] == "right"
    assert candidate["reference_url"] is not None
    assert candidate["providers"] == ["test-provider"]
    vibemon_id = candidate["id"]

    facing_calls_after_generate = _FakeAssetGenerator.facing_calls
    current = await client.get("/api/candidates/current")
    assert current.status_code == 200
    current_candidate = current.json()["candidate"]
    assert current_candidate["id"] == vibemon_id
    assert current_candidate["providers"] == ["test-provider"]
    assert current_candidate["reference_facing"] == "right"
    assert current_candidate["reference_url"] is not None
    assert _FakeAssetGenerator.facing_calls == facing_calls_after_generate

    adopted = await client.post(
        f"/api/candidates/{vibemon_id}/adopt",
        json={"nickname": "Sparky"},
    )
    assert adopted.status_code == 201
    adopted_payload = adopted.json()
    assert adopted_payload["crew_count"] == 1
    assert adopted_payload["candidate"]["nickname"] == "Sparky"

    crew = await client.get("/api/trainers/crew")
    assert crew.status_code == 200
    members = crew.json()["members"]
    assert len(members) == 1
    assert members[0]["nickname"] == "Sparky"
    assert members[0]["id"] == vibemon_id

    me = await client.get("/api/trainers/me")
    assert me.json()["crew_count"] == 1
    assert me.json()["id"] == trainer_id


async def test_reject_candidate_blocked_for_first_vibemon(client: AsyncTestClient) -> None:
    await _register(client)
    generated = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    vibemon_id = generated.json()["candidate"]["id"]

    rejected = await client.post(f"/api/candidates/{vibemon_id}/reject")
    assert rejected.status_code == 422
    assert rejected.json()["code"] == InterfaceErrorCode.CANDIDATE_REVIEW_UNAVAILABLE.value


async def test_reject_candidate_allowed_with_one_crew_member(client: AsyncTestClient) -> None:
    await _register(client)
    first = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    first_id = first.json()["candidate"]["id"]
    adopted = await client.post(f"/api/candidates/{first_id}/adopt", json={"nickname": "Keeper"})
    assert adopted.status_code == 201
    assert adopted.json()["crew_count"] == 1

    second = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    second_id = second.json()["candidate"]["id"]

    rejected = await client.post(f"/api/candidates/{second_id}/reject")
    assert rejected.status_code == 201

    crew = await client.get("/api/trainers/crew")
    assert len(crew.json()["members"]) == 1


async def test_refresh_candidate_redraws_reference(client: AsyncTestClient) -> None:
    await _register(client)
    generated = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    vibemon_id = generated.json()["candidate"]["id"]

    refreshed = await client.post(f"/api/candidates/{vibemon_id}/refresh")
    assert refreshed.status_code == 201
    assert refreshed.json()["candidate"]["reference_url"] is not None


async def _generate_and_adopt(client: AsyncTestClient, *, nickname: str) -> None:
    generated = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert generated.status_code == 201
    vibemon_id = generated.json()["candidate"]["id"]
    adopted = await client.post(f"/api/candidates/{vibemon_id}/adopt", json={"nickname": nickname})
    assert adopted.status_code == 201


async def test_generate_candidate_bypass_credits_skips_daily_limit(client: AsyncTestClient) -> None:
    await _register(client)
    for index in range(credits.DAILY_GENERATION_CREDITS):
        await _generate_and_adopt(client, nickname=f"Keeper{index}")

    blocked = await client.post(
        "/api/candidates/generate",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == InterfaceErrorCode.GENERATION_CREDIT_UNAVAILABLE.value

    bypassed = await client.post(
        "/api/candidates/generate?bypass-credits=true",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert bypassed.status_code == 201


async def test_generate_candidate_bypass_credits_rejected_in_prod(
    client: AsyncTestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.settings import Settings

    await _register(client)
    monkeypatch.setenv("VIBEMON_ENVIRONMENT", "prod")
    Settings.load(refresh=True)

    response = await client.post(
        "/api/candidates/generate?bypass-credits=true",
        json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Generation credit bypass is not available in production."
