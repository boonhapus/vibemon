"""Per-trainer provider prefetch timestamps (Redis when available)."""

from urllib.parse import urlsplit
import datetime as dt
import uuid

from app.settings import Settings
from app.storage.cache import redis as cache_redis

_NAMESPACE = "vibemon_provider_prefetch"


def _redis_url() -> str | None:
    cache_url = Settings.load().storage.cache
    if urlsplit(cache_url).scheme not in ("redis", "rediss"):
        return None
    return cache_url


def _prefetch_key(trainer_id: uuid.UUID, provider_id: str) -> str:
    return f"{_NAMESPACE}:{trainer_id}:{provider_id}"


async def record_prefetch(
    trainer_id: uuid.UUID,
    provider_id: str,
    prefetched_at: dt.datetime,
) -> None:
    """Persist the last successful prefetch time when Redis is configured."""
    url = _redis_url()
    if url is None:
        return
    client = cache_redis._shared_async_client(url)
    await client.set(_prefetch_key(trainer_id, provider_id), prefetched_at.isoformat())


async def get_prefetched_at(trainer_id: uuid.UUID, provider_id: str) -> dt.datetime | None:
    """Return the last successful prefetch time, if recorded."""
    url = _redis_url()
    if url is None:
        return None
    client = cache_redis._shared_async_client(url)
    raw = await client.get(_prefetch_key(trainer_id, provider_id))
    if raw is None:
        return None
    text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed


async def list_prefetched_at(
    trainer_id: uuid.UUID,
    provider_ids: tuple[str, ...],
) -> dict[str, dt.datetime]:
    """Batch-read prefetch timestamps for catalog providers."""
    url = _redis_url()
    if url is None or not provider_ids:
        return {}
    client = cache_redis._shared_async_client(url)
    keys = [_prefetch_key(trainer_id, provider_id) for provider_id in provider_ids]
    values = await client.mget(keys)
    timestamps: dict[str, dt.datetime] = {}
    for provider_id, raw in zip(provider_ids, values, strict=True):
        if raw is None:
            continue
        text = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        parsed = dt.datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.UTC)
        timestamps[provider_id] = parsed
    return timestamps
