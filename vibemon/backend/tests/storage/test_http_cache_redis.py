from typing import Any
from unittest.mock import patch
import time

from niquests_cache.typing import CacheEntry
import fakeredis
import fakeredis.aioredis
import niquests
import pytest

from app.providers._api.session import CachedAPIClient
from app.settings import Settings
from app.storage.cache.redis import CacheBustingBackend, RedisBackend, cache_busting_enabled, make_cache_backend


def _sample_entry(*, url: str = "https://example.test/recording") -> CacheEntry:
    return {
        "content": b'{"recordings":[]}',
        "encoding": "utf-8",
        "headers": {"content-type": "application/json"},
        "status_code": 200,
        "ts": time.time(),
        "url": url,
    }


@pytest.fixture
def redis_backend() -> RedisBackend:
    return RedisBackend(
        url="redis://unused",
        namespace="musicbrainz_web_api",
        client=fakeredis.FakeStrictRedis(decode_responses=False),
        async_client=fakeredis.aioredis.FakeRedis(decode_responses=False),
    )


def test_redis_backend_rejects_invalid_namespace() -> None:
    with pytest.raises(ValueError, match="Invalid namespace"):
        RedisBackend(url="redis://localhost:6379/0", namespace="bad-namespace")


def test_redis_backend_sync_round_trip(redis_backend: RedisBackend) -> None:
    entry = _sample_entry()
    redis_backend.set("cache-key", entry)

    stored = redis_backend.get("cache-key")

    assert stored == entry


@pytest.mark.asyncio
async def test_redis_backend_async_round_trip(redis_backend: RedisBackend) -> None:
    entry = _sample_entry(url="https://example.test/async")
    await redis_backend.aset("async-key", entry)

    stored = await redis_backend.aget("async-key")

    assert stored == entry


def test_redis_backend_namespace_isolation(redis_backend: RedisBackend) -> None:
    other = RedisBackend(
        url="redis://unused",
        namespace="lastfm_web_api",
        client=redis_backend._client,
        async_client=redis_backend._async_client,
    )
    entry = _sample_entry()
    redis_backend.set("shared-key", entry)

    assert other.get("shared-key") is None


def test_make_cache_backend_uses_sqlite_when_cache_url_is_sqlite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEMON_BUST_CACHE", raising=False)
    monkeypatch.setenv("VIBEMON_STORAGE__CACHE", "sqlite:///tmp/vibemon-api-cache.db")
    Settings.load(refresh=True)

    backend = make_cache_backend("musicbrainz_web_api")

    assert backend.__class__.__name__ == "SQLiteBackend"


def test_make_cache_backend_uses_redis_when_cache_url_is_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEMON_BUST_CACHE", raising=False)
    monkeypatch.setenv("VIBEMON_STORAGE__CACHE", "redis://localhost:6379/0")
    Settings.load(refresh=True)

    backend = make_cache_backend("musicbrainz_web_api")

    assert isinstance(backend, RedisBackend)
    assert backend.namespace == "musicbrainz_web_api"


def test_make_cache_backend_uses_redis_when_cache_url_is_rediss(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VIBEMON_BUST_CACHE", raising=False)
    monkeypatch.setenv("VIBEMON_STORAGE__CACHE", "rediss://localhost:6380/0")
    Settings.load(refresh=True)

    backend = make_cache_backend("musicbrainz_web_api")

    assert isinstance(backend, RedisBackend)


def test_make_cache_backend_bypasses_cache_when_cache_busting_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEMON_BUST_CACHE", "1")
    monkeypatch.setenv("VIBEMON_STORAGE__CACHE", "sqlite:///tmp/vibemon-api-cache.db")
    Settings.load(refresh=True)

    backend = make_cache_backend("musicbrainz_web_api")

    assert isinstance(backend, CacheBustingBackend)


def test_cache_busting_backend_skips_reads_but_writes_through(redis_backend: RedisBackend) -> None:
    backend = CacheBustingBackend(redis_backend)
    entry = _sample_entry()
    redis_backend.set("cache-key", entry)

    assert backend.get("cache-key") is None
    backend.set("fresh-key", entry)
    assert redis_backend.get("fresh-key") == entry


@pytest.mark.parametrize("value", ["", "0", "false", "False", "no", "off"])
def test_cache_busting_disabled_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("VIBEMON_BUST_CACHE", value)

    assert cache_busting_enabled() is False


def _upstream_json_response(url: str) -> niquests.Response:
    response = niquests.Response()
    response.status_code = 200
    response._content = b'{"ok": true}'
    response._content_consumed = True
    response.url = url
    response.encoding = "utf-8"
    response.headers["content-type"] = "application/json"
    return response


@pytest.mark.asyncio
async def test_cached_api_client_serves_repeat_get_from_redis_backend() -> None:
    backend = RedisBackend(
        url="redis://unused",
        namespace="integration_test",
        client=fakeredis.FakeStrictRedis(decode_responses=False),
        async_client=fakeredis.aioredis.FakeRedis(decode_responses=False),
    )
    upstream_calls = 0

    async def upstream_request(_self: Any, method: str, url: str, *_args: Any, **_kwargs: Any) -> niquests.Response:
        nonlocal upstream_calls
        upstream_calls += 1
        return _upstream_json_response(url)

    client = CachedAPIClient(
        backend=backend,
        expire_after=3600,
        base_url="https://example.test",
    )

    with patch.object(niquests.AsyncSession, "request", upstream_request):
        first = await client.get("/resource")
        second = await client.get("/resource")

    assert upstream_calls == 1
    assert first.content == second.content
    assert first.status_code == second.status_code == 200
