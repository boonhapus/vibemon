from typing import Any
import asyncio
import collections
import contextvars
import dataclasses
import datetime as dt
import time

from niquests.typing import HookType
import niquests
import structlog

_LOGGER = structlog.get_logger(__name__)
_THROTTLE_HELD: contextvars.ContextVar[bool] = contextvars.ContextVar("throttled_session_slot_held", default=False)

type HookValue = niquests.AsyncResponse | niquests.PreparedRequest | niquests.Response


class LoggingHook(niquests.AsyncLifeCycleHook[HookValue]):
    """Structured logging hook for an API client."""

    def __init__(self, provider: str) -> None:
        super().__init__()
        self.provider = provider

    async def pre_request(self, prepared_request: niquests.PreparedRequest, **_kwargs: Any) -> None:
        """
        The prepared request just got built. You may alter it prior to be sent through HTTP.

        Further reading:
          https://niquests.readthedocs.io/en/latest/user/advanced.html#niquests.hooks.AsyncLifeCycleHook.pre_request
        """
        await _LOGGER.adebug(
            f"{self.provider}.request",
            method=prepared_request.method,
            url=str(prepared_request.url),
            body=prepared_request.body,
        )

    async def response(self, response: niquests.Response, **_kwargs: Any) -> None:
        """
        The response generated from a Request. You may alter the response at will.

        Further reading:
          https://niquests.readthedocs.io/en/latest/user/advanced.html#niquests.hooks.AsyncLifeCycleHook.response
        """
        if response.request is None:
            return

        await _LOGGER.adebug(
            f"{self.provider}.response",
            method=response.request.method,
            url=str(response.request.url),
            status_code=response.status_code,
            elapsed_s=round(response.elapsed.total_seconds(), 2),
        )


@dataclasses.dataclass
class RateLimitState:
    """Track the state of a given limit."""

    max_requests: int
    window_seconds: float
    timestamps: collections.deque[float] = dataclasses.field(default_factory=collections.deque)
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


class RateLimiterHook(niquests.AsyncLifeCycleHook[HookValue]):
    """
    A sliding window rate limiter hook for an API client.

    This hook ensures that outgoing requests comply with one or more rate limits
    (e.g., 10 requests per second and 1000 requests per hour). It uses
    `time.monotonic()` for precision and `asyncio.Lock` for thread-safe
    asynchronous execution.

    Optional ``concurrency`` caps in-flight requests (e.g. ``1`` for a mutex).
    Pair with :class:`ThrottledSessionMixin` so slots are released even when
    ``send()`` raises. ``None`` means no in-flight cap.
    """

    def __init__(
        self,
        *limits: tuple[int, dt.timedelta],
        provider: str,
        concurrency: int | None = None,
    ) -> None:
        super().__init__()
        self.provider = provider
        self._states = [RateLimitState(req, win.total_seconds()) for req, win in limits]

        if concurrency is not None and concurrency < 1:
            raise ValueError(f"concurrency must be at least 1, got {concurrency}")

        self._semaphore = asyncio.Semaphore(concurrency) if concurrency is not None else None

        for state in self._states:
            rps = round(state.max_requests / state.window_seconds, 2)
            _LOGGER.debug(f"Rate limit for {provider}: {state.max_requests} reqs / {state.window_seconds}s ({rps} RPS)")

        if self._semaphore is not None:
            _LOGGER.debug(f"Concurrency limit for {provider}: {concurrency}")

    async def acquire_concurrency(self) -> bool:
        """Acquire an in-flight slot when ``concurrency`` is configured."""
        if self._semaphore is None:
            return False
        await self._semaphore.acquire()
        return True

    def release_concurrency(self) -> None:
        """Release an in-flight slot acquired by :meth:`acquire_concurrency`."""
        if self._semaphore is not None:
            self._semaphore.release()

    async def pre_request(self, prepared_request: niquests.PreparedRequest, **_kwargs: Any) -> None:
        """
        The prepared request just got built. You may alter it prior to be sent through HTTP.

        This method iterates through all registered limits sequentially. If a limit is
        reached, it pauses execution (yielding to the event loop) until a  slot becomes
        available.

        Further reading:
          https://niquests.readthedocs.io/en/latest/user/advanced.html#niquests.hooks.AsyncLifeCycleHook.pre_request
        """
        # Check all limits before proceeding
        for state in self._states:
            await self._apply_limit(state)

    async def _apply_limit(self, state: RateLimitState) -> None:
        """
        Enforces a single rate limit state.

        Uses a sliding window algorithm:
        1. Cleans up timestamps older than the window duration.
        2. If capacity exists, records the current time and returns.
        3. If at capacity, calculates the wait time until the oldest request expires
           and sleeps before retrying.
        """
        while True:
            wait_for = 0.0

            async with state.lock:
                now = time.monotonic()

                # Clear expired timestamps
                while state.timestamps and now - state.timestamps[0] >= state.window_seconds:
                    state.timestamps.popleft()

                # Capacity available
                if len(state.timestamps) < state.max_requests:
                    state.timestamps.append(now)
                    return

                # Capacity full: calculate sleep time based on the oldest request
                wait_for = (state.timestamps[0] + state.window_seconds) - now

            # Sleep outside the lock to allow other tasks to check/cleanup their own state
            if wait_for > 0:
                await asyncio.sleep(wait_for)


class ThrottledSessionMixin:
    """Wrap ``send()`` so :class:`RateLimiterHook` concurrency slots survive errors."""

    @staticmethod
    def discover_hooks(hooks: HookType[niquests.Response | niquests.PreparedRequest]) -> RateLimiterHook | None:
        """Attempt to find the RateLimiterHook."""
        for hook_fns in hooks.values():
            for fn in hook_fns:
                owner = getattr(fn, "__self__", None)

                if isinstance(owner, RateLimiterHook):
                    return owner

        return None

    async def send(self, request: niquests.PreparedRequest, **kwargs: Any) -> niquests.Response:
        # Redirect/retry hops re-enter send() while the parent still holds the
        # slot. Acquiring again would deadlock once the pool is saturated, so
        # nested sends pass through on the slot the outer call already holds.
        if _THROTTLE_HELD.get():
            return await super().send(request, **kwargs)  # type: ignore[misc]

        rate_limiter = self.discover_hooks(request.hooks) or self.discover_hooks(getattr(self, "hooks", {}))
        acquired = False if rate_limiter is None else await rate_limiter.acquire_concurrency()

        token = _THROTTLE_HELD.set(True)

        try:
            return await super().send(request, **kwargs)  # type: ignore[misc]
        finally:
            _THROTTLE_HELD.reset(token)

            if rate_limiter is not None and acquired:
                rate_limiter.release_concurrency()
