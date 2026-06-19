"""Tests for shared provider hooks."""

import asyncio
import datetime as dt

import pytest

from app import __project__
from app.providers._api import rate_limits
from app.providers._api.hooks import RateLimiterHook
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.settings import Settings


def test_provider_default_headers() -> None:
    headers = provider_default_headers()
    assert headers["accept"] == "application/json"
    slug = __project__.__slug__
    expected = f"{__project__.__name__} v{__project__.__version__} (+github/{slug})"
    assert headers["user-agent"] == expected


def test_provider_retry_policy_retries_transient_status_codes() -> None:
    policy = provider_retry_policy()
    assert policy.total == 5
    assert policy.backoff_factor == 2
    assert 429 in policy.status_forcelist
    assert 503 in policy.status_forcelist
    assert policy.respect_retry_after_header is True
    assert policy.raise_on_status is False


def test_rate_limiter_rejects_invalid_concurrency() -> None:
    with pytest.raises(ValueError, match="concurrency must be at least 1"):
        RateLimiterHook((1, dt.timedelta(seconds=1)), provider="test", concurrency=0)


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_serializes_in_flight() -> None:
    hook = RateLimiterHook((100, dt.timedelta(seconds=1)), provider="test", concurrency=1)
    in_flight = 0
    max_in_flight = 0
    counter_lock = asyncio.Lock()

    async def simulate_request() -> None:
        nonlocal in_flight, max_in_flight
        acquired = await hook.acquire_concurrency()
        try:
            async with counter_lock:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
            await asyncio.sleep(0.05)
            async with counter_lock:
                in_flight -= 1
        finally:
            if acquired:
                hook.release_concurrency()

    async with asyncio.TaskGroup() as tg:
        for _ in range(5):
            tg.create_task(simulate_request())

    assert max_in_flight == 1


@pytest.mark.asyncio
async def test_rate_limiter_concurrency_none_allows_parallel_in_flight(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    Settings.load(refresh=True)
    hook = RateLimiterHook((100, dt.timedelta(seconds=1)), provider="test", concurrency=None)
    in_flight = 0
    max_in_flight = 0
    counter_lock = asyncio.Lock()

    async def simulate_request() -> None:
        nonlocal in_flight, max_in_flight
        acquired = await hook.acquire_concurrency()
        assert acquired is False
        async with counter_lock:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        await asyncio.sleep(0.05)
        async with counter_lock:
            in_flight -= 1

    async with asyncio.TaskGroup() as tg:
        for _ in range(5):
            tg.create_task(simulate_request())

    assert max_in_flight == 5


def test_shared_rate_limiters_reuse_same_hook() -> None:
    from app.providers.climate.openmeteo import const as openmeteo_const

    rate_limits.clear_shared_rate_limiters()
    weather = rate_limits.shared(
        openmeteo_const.QUOTA_KEY,
        provider="open-meteo.weather_forecast",
        limits=openmeteo_const.RATE_LIMITS,
        concurrency=openmeteo_const.CONCURRENCY,
    )
    elevation = rate_limits.shared(
        openmeteo_const.QUOTA_KEY,
        provider="open-meteo.elevation",
        limits=openmeteo_const.RATE_LIMITS,
        concurrency=openmeteo_const.CONCURRENCY,
    )
    assert weather is elevation
