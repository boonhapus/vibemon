"""Redis and SQLite backends for niquests-cache HTTP response storage."""

from typing import cast, override
from urllib.parse import urlsplit
from urllib.request import url2pathname
import base64
import contextlib
import contextvars
import functools as ft
import json
import os
import pathlib
import re

from niquests_cache.backends import SQLiteBackend
from niquests_cache.backends.base import BaseBackend
from niquests_cache.typing import CacheEntry
import redis
import redis.asyncio as aioredis

from app.settings import Settings

_NAMESPACE_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BUST_CACHE_ENV = "VIBEMON_BUST_CACHE"
_FALSE_ENV_VALUES = {"", "0", "false", "no", "off"}
_request_cache_bust = contextvars.ContextVar("request_cache_bust", default=False)


def _validate_namespace(name: str) -> str:
    """Reject cache key namespaces that would be awkward in Redis."""
    if not _NAMESPACE_PATTERN.match(name):
        msg = f"Invalid namespace: {name!r}."
        raise ValueError(msg)
    return name


def _redis_key(namespace: str, key: str) -> str:
    return f"{namespace}:{key}"


def _entry_to_bytes(entry: CacheEntry) -> bytes:
    payload = {
        "content": base64.b64encode(entry["content"]).decode("ascii"),
        "encoding": entry["encoding"],
        "headers": dict(entry["headers"]),
        "status_code": entry["status_code"],
        "ts": entry["ts"],
        "url": entry["url"],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def _bytes_to_entry(data: bytes) -> CacheEntry:
    payload = json.loads(data.decode("utf-8"))
    return {
        "content": base64.b64decode(payload["content"]),
        "encoding": payload["encoding"],
        "headers": cast("dict[str, str]", payload["headers"]),
        "status_code": payload["status_code"],
        "ts": payload["ts"],
        "url": payload["url"],
    }


@ft.cache
def _shared_sync_client(url: str) -> redis.Redis:
    return redis.from_url(url, decode_responses=False)


@ft.cache
def _shared_async_client(url: str) -> aioredis.Redis:
    return aioredis.from_url(url, decode_responses=False)


class RedisBackend(BaseBackend):
    """Cache HTTP responses in Redis, namespaced by provider."""

    def __init__(
        self,
        url: str,
        *,
        namespace: str = "niquests_cache",
        client: redis.Redis | None = None,
        async_client: aioredis.Redis | None = None,
    ) -> None:
        self._url = url
        self._namespace = _validate_namespace(namespace)
        self._client = client or _shared_sync_client(url)
        self._async_client = async_client or _shared_async_client(url)

    @property
    def url(self) -> str:
        """Redis connection URL."""
        return self._url

    @property
    def namespace(self) -> str:
        """Key prefix isolating one provider's cache entries."""
        return self._namespace

    @override
    def get(self, key: str) -> CacheEntry | None:
        data = self._client.get(_redis_key(self._namespace, key))
        if data is None:
            return None
        return _bytes_to_entry(cast("bytes", data))

    @override
    def set(self, key: str, entry: CacheEntry) -> None:
        self._client.set(_redis_key(self._namespace, key), _entry_to_bytes(entry))

    @override
    async def aget(self, key: str) -> CacheEntry | None:
        data = await self._async_client.get(_redis_key(self._namespace, key))
        if data is None:
            return None
        return _bytes_to_entry(cast("bytes", data))

    @override
    async def aset(self, key: str, entry: CacheEntry) -> None:
        await self._async_client.set(_redis_key(self._namespace, key), _entry_to_bytes(entry))


class CacheBustingBackend(BaseBackend):
    """Force cache misses while preserving writes to the configured backend."""

    def __init__(self, backend: BaseBackend) -> None:
        self._backend = backend

    @property
    def backend(self) -> BaseBackend:
        return self._backend

    @override
    def get(self, key: str) -> CacheEntry | None:
        return None

    @override
    def set(self, key: str, entry: CacheEntry) -> None:
        self._backend.set(key, entry)

    @override
    async def aget(self, key: str) -> CacheEntry | None:
        return None

    @override
    async def aset(self, key: str, entry: CacheEntry) -> None:
        await self._backend.aset(key, entry)


def _sqlite_database_path(cache_url: str) -> pathlib.Path:
    parts = urlsplit(cache_url)
    if parts.scheme != "sqlite":
        msg = f"Expected sqlite cache URL, got {cache_url!r}"
        raise ValueError(msg)
    return pathlib.Path(url2pathname(parts.path))


def cache_busting_enabled() -> bool:
    value = os.environ.get(_BUST_CACHE_ENV, "")
    return value.strip().lower() not in _FALSE_ENV_VALUES


def cache_busting_active() -> bool:
    return cache_busting_enabled() or _request_cache_bust.get()


@contextlib.contextmanager
def bypass_http_cache():
    """Force HTTP cache misses for provider prefetch refresh within this context."""
    token = _request_cache_bust.set(True)
    try:
        yield
    finally:
        _request_cache_bust.reset(token)


def make_cache_backend(namespace: str) -> RedisBackend | SQLiteBackend | CacheBustingBackend:
    """Return a niquests-cache backend from ``Settings.load().storage.cache``."""
    cache_url = Settings.load().storage.cache
    scheme = urlsplit(cache_url).scheme

    if scheme in ("redis", "rediss"):
        backend = RedisBackend(url=cache_url, namespace=namespace)
    else:
        backend = SQLiteBackend(
            database=_sqlite_database_path(cache_url),
            table_name=namespace,
        )

    if cache_busting_active():
        return CacheBustingBackend(backend)
    return backend
