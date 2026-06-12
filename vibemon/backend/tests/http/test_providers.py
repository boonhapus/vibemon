"""HTTP provider catalog route tests."""

from litestar.testing import AsyncTestClient
import pytest

from app.http.app import create_app


@pytest.fixture
def http_app():
    return create_app()


@pytest.fixture
async def client(http_app):
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


async def test_list_providers_returns_catalog(client: AsyncTestClient) -> None:
    response = await client.get("/api/providers/")
    assert response.status_code == 200
    payload = response.json()
    providers = payload["providers"]
    assert [entry["id"] for entry in providers] == [
        "climate",
        "biome",
        "celestial",
        "music",
        "video",
        "books",
        "fitness",
    ]
    climate = providers[0]
    assert climate["label"] == "SKY"
    assert climate["implemented"] is True
    assert climate["requirements"][0]["kind"] == "geolocation"
    assert climate["lore"]
    assert climate["elements"]
    music = next(entry for entry in providers if entry["id"] == "music")
    assert music["implemented"] is False


async def test_provider_status_requires_session(client: AsyncTestClient) -> None:
    response = await client.get("/api/providers/status")
    assert response.status_code == 401


async def test_provider_status_reports_music_unimplemented(client: AsyncTestClient) -> None:
    register = await client.post("/api/trainers/register", json={"username": "ProviderAda"})
    assert register.status_code == 201

    response = await client.get("/api/providers/status", params={"latitude": 51.5, "longitude": -0.1})
    assert response.status_code == 200
    statuses = {entry["id"]: entry for entry in response.json()["providers"]}
    assert statuses["climate"]["ready"] is True
    assert statuses["music"]["ready"] is False
    assert statuses["music"]["requirements"]["lastfm.link"]["status"] == "unavailable"


async def test_prefetch_climate_requires_geolocation(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    register = await client.post("/api/trainers/register", json={"username": "ClimateTrainer"})
    assert register.status_code == 201

    response = await client.post("/api/providers/climate/prefetch", json={})
    assert response.status_code == 422
    assert response.json()["code"] == "provider_config_required"


async def test_prefetch_climate_warms_provider(client: AsyncTestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.providers import registry as provider_registry
    from app.providers.climate import schema as climate_schema
    from app.providers.climate.provider import ClimateProvider

    register = await client.post("/api/trainers/register", json={"username": "WarmTrainer"})
    assert register.status_code == 201

    called = {"fetch": False}

    class MockClimateProvider(ClimateProvider):
        async def fetch(self, seed, *, secrets=None):
            called["fetch"] = True
            return climate_schema.ClimatePayload(
                start_date="2026-01-01",
                end_date="2026-01-07",
                weather_augmented={},
            )

    original_get = provider_registry.get_catalog_provider

    def get_provider(name: str):
        if name == "climate":
            return MockClimateProvider
        return original_get(name)

    monkeypatch.setattr("app.http.routes.providers.registry.get_catalog_provider", get_provider)

    response = await client.post(
        "/api/providers/climate/prefetch",
        json={"latitude": 51.5, "longitude": -0.1, "force_refresh": True},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["prefetched_at"]
    assert called["fetch"] is True
