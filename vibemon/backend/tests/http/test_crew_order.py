"""HTTP tests for crew listing facing data and crew reorder."""

import io
import uuid

from litestar.testing import AsyncTestClient
from PIL import Image
import pytest

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
    async def detect_trainer_reference_facing(self, reference_png: bytes):
        from app.domains.sprite import types as sprite_types

        return sprite_types.SpriteFacing.RIGHT

    async def detect_vibemon_reference_facing(self, reference_png: bytes, *, vibemon_name: str):
        from app.domains.sprite import types as sprite_types

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
    monkeypatch.setattr(genai_assets, "get_default_asset_generator", lambda: _FakeAssetGenerator())
    get_default_monstore.cache_clear()


@pytest.fixture(autouse=True)
def fake_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.providers.registry.build_provider_instances",
        lambda provider_names=None: [FakeProvider()],
    )


async def _register(client: AsyncTestClient, username: str = "Rotator") -> str:
    response = await client.post("/api/trainers/register", json={"username": username})
    assert response.status_code == 201
    return response.json()["id"]


async def _adopt_crew(client: AsyncTestClient, count: int) -> list[str]:
    ids: list[str] = []
    for index in range(count):
        generated = await client.post(
            "/api/candidates/generate",
            json={"providers": ["climate"], "latitude": 41.88, "longitude": -87.63},
        )
        assert generated.status_code == 201
        vibemon_id = generated.json()["candidate"]["id"]
        adopted = await client.post(f"/api/candidates/{vibemon_id}/adopt", json={"nickname": f"Mon{index}"})
        assert adopted.status_code == 201
        ids.append(vibemon_id)
    return ids


async def test_crew_member_exposes_reference_detected_facing(client: AsyncTestClient) -> None:
    await _register(client)
    await _adopt_crew(client, 1)

    crew = await client.get("/api/trainers/crew")
    assert crew.status_code == 200
    members = crew.json()["members"]
    assert len(members) == 1
    assert members[0]["reference_detected_facing"] == "RIGHT"


async def test_reorder_crew_requires_session(client: AsyncTestClient) -> None:
    response = await client.put(
        "/api/trainers/crew/order",
        json={"members": [{"id": str(uuid.uuid4()), "crew_slot": 0}]},
    )
    assert response.status_code == 401


async def test_reorder_crew_rotates_slots(client: AsyncTestClient) -> None:
    await _register(client)
    ids = await _adopt_crew(client, 3)

    # Rotate by one: slot 1 becomes lead.
    payload = {
        "members": [
            {"id": ids[0], "crew_slot": 2},
            {"id": ids[1], "crew_slot": 0},
            {"id": ids[2], "crew_slot": 1},
        ]
    }
    response = await client.put("/api/trainers/crew/order", json=payload)
    assert response.status_code == 200
    members = response.json()["members"]
    assert [member["id"] for member in members] == [ids[1], ids[2], ids[0]]
    assert [member["crew_slot"] for member in members] == [0, 1, 2]

    # The new order persists on a fresh read.
    crew = await client.get("/api/trainers/crew")
    assert [member["id"] for member in crew.json()["members"]] == [ids[1], ids[2], ids[0]]


async def test_reorder_crew_rejects_partial_order(client: AsyncTestClient) -> None:
    await _register(client)
    ids = await _adopt_crew(client, 2)

    response = await client.put(
        "/api/trainers/crew/order",
        json={"members": [{"id": ids[0], "crew_slot": 0}]},
    )
    assert response.status_code == 400

    # Order unchanged.
    crew = await client.get("/api/trainers/crew")
    assert [member["id"] for member in crew.json()["members"]] == ids


async def test_reorder_crew_rejects_duplicate_slots(client: AsyncTestClient) -> None:
    await _register(client)
    ids = await _adopt_crew(client, 2)

    response = await client.put(
        "/api/trainers/crew/order",
        json={
            "members": [
                {"id": ids[0], "crew_slot": 0},
                {"id": ids[1], "crew_slot": 0},
            ]
        },
    )
    assert response.status_code == 400


async def test_reorder_crew_rejects_out_of_range_slot(client: AsyncTestClient) -> None:
    await _register(client)
    ids = await _adopt_crew(client, 1)

    response = await client.put(
        "/api/trainers/crew/order",
        json={"members": [{"id": ids[0], "crew_slot": 6}]},
    )
    assert response.status_code == 400


async def test_reorder_crew_rejects_foreign_vibemon(client: AsyncTestClient) -> None:
    await _register(client)
    ids = await _adopt_crew(client, 1)

    response = await client.put(
        "/api/trainers/crew/order",
        json={
            "members": [
                {"id": ids[0], "crew_slot": 0},
                {"id": str(uuid.uuid4()), "crew_slot": 1},
            ]
        },
    )
    assert response.status_code == 400
