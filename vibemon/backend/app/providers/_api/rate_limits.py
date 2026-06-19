"""Process-wide upstream rate limit registry.

Maps a quota key to one :class:`RateLimiterHook` per process. Limit tuples and
concurrency caps live with each provider client; this module only deduplicates
hook instances.

See ``docs/development/ideas/redis-backed-provider-rate-limits.md`` for moving
coordination to Redis when multiple workers run.
"""

import datetime as dt

from app.providers._api.hooks import RateLimiterHook

type RateLimitSpec = tuple[tuple[int, dt.timedelta], ...]

_SHARED: dict[str, RateLimiterHook] = {}
_SPECS: dict[str, tuple[RateLimitSpec, int | None]] = {}


def clear_shared_rate_limiters() -> None:
    """Drop cached limiters (tests only)."""
    _SHARED.clear()
    _SPECS.clear()


def shared(
    quota_key: str,
    *,
    provider: str,
    limits: RateLimitSpec,
    concurrency: int | None = None,
) -> RateLimiterHook:
    """Return the process-wide limiter for ``quota_key``, creating it on first use."""
    spec = (limits, concurrency)
    existing = _SHARED.get(quota_key)
    if existing is not None:
        if _SPECS[quota_key] != spec:
            raise ValueError(f"rate limit spec mismatch for {quota_key!r}")
        return existing

    hook = RateLimiterHook(*limits, provider=provider, concurrency=concurrency)
    _SHARED[quota_key] = hook
    _SPECS[quota_key] = spec
    return hook
