import asyncio
import collections
import dataclasses
import datetime as dt
import time

import niquests
import structlog

_LOGGER = structlog.get_logger(__name__)


class LoggingHook(niquests.AsyncLifeCycleHook):
    """Structured logging hook for an API client."""

    def __init__(self, provider: str) -> None:
        super().__init__()
        self.provider = provider

    async def pre_request(self, prepared_request: niquests.PreparedRequest, **kwargs) -> None:
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

    async def response(self, response: niquests.Response, **kwargs) -> None:
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
    timestamps: collections.deque = dataclasses.field(default_factory=collections.deque)
    lock: asyncio.Lock = dataclasses.field(default_factory=asyncio.Lock)


class RateLimiterHook(niquests.AsyncLifeCycleHook):
    """
    A sliding window rate limiter hook for an API client.
    
    This hook ensures that outgoing requests comply with one or more rate limits
    (e.g., 10 requests per second and 1000 requests per hour). It uses
    `time.monotonic()` for precision and `asyncio.Lock` for thread-safe 
    asynchronous execution.
    """

    def __init__(self, *limits: tuple[int, dt.timedelta], provider: str) -> None:
        super().__init__()
        self.provider = provider
        self._states = [RateLimitState(req, win.total_seconds()) for req, win in limits]
        
        for state in self._states:
            rps = round(state.max_requests / state.window_seconds, 2)
            _LOGGER.debug(f"Rate limit for {provider}: {state.max_requests} reqs / {state.window_seconds}s ({rps} RPS)")

    async def pre_request(self, prepared_request: niquests.PreparedRequest, **kwargs) -> None:
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
            wait_for = 0
            
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
