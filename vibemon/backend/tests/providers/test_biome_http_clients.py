"""HTTP client behavior for biome provider upstream APIs."""

from typing import Any
from unittest.mock import patch
import asyncio
import json

import fakeredis
import fakeredis.aioredis
import niquests
import pytest

from app.providers.biome.water.overpass import api as overpass_api
from app.storage.cache.redis import RedisBackend


def _overpass_json_response(*, url: str, elements: list[dict[str, Any]] | None = None) -> niquests.Response:
    response = niquests.Response()
    response.status_code = 200
    response._content = json.dumps({"elements": elements or []}).encode("utf-8")
    response._content_consumed = True
    response.url = url
    response.encoding = "utf-8"
    response.headers["content-type"] = "application/json"
    return response


@pytest.mark.asyncio
async def test_overpass_proximity_queries_marine_and_inland_in_parallel() -> None:
    in_flight = 0
    max_in_flight = 0
    lock = asyncio.Lock()
    client = overpass_api.OverpassWaterClient()

    async def mock_get(_self: Any, _method: str, url: str, **_kwargs: Any) -> niquests.Response:
        nonlocal in_flight, max_in_flight
        async with lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with lock:
            in_flight -= 1
        return _overpass_json_response(url=url)

    with patch.object(niquests.AsyncSession, "request", mock_get):
        result = await client.proximity(41.8781, -87.6298)

    assert max_in_flight == 2
    assert result == {
        "nearest_marine_km": None,
        "marine_feature": None,
        "nearest_inland_water_km": None,
        "inland_feature": None,
    }


@pytest.mark.asyncio
async def test_overpass_cached_client_serves_repeat_queries_from_cache() -> None:
    backend = RedisBackend(
        url="redis://unused",
        namespace="overpass_water_api",
        client=fakeredis.FakeStrictRedis(decode_responses=False),
        async_client=fakeredis.aioredis.FakeRedis(decode_responses=False),
    )
    upstream_calls = 0

    async def upstream_request(_self: Any, _method: str, url: str, *_args: Any, **_kwargs: Any) -> niquests.Response:
        nonlocal upstream_calls
        upstream_calls += 1
        return _overpass_json_response(url=url)

    client = overpass_api.OverpassWaterClient(backend=backend)

    with patch.object(niquests.AsyncSession, "request", upstream_request):
        first = await client.proximity(41.8781, -87.6298)
        second = await client.proximity(41.8781, -87.6298)

    assert upstream_calls == 2
    assert first == second
