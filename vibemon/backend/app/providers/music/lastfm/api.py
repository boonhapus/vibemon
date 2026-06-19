"""Last.fm Web API client for the music provider."""

from typing import Any
import datetime as dt

import niquests

from app.providers._api import rate_limits
from app.providers._api.hooks import LoggingHook
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.providers._api.session import CachedAPIClient
from app.settings import Settings
from app.storage.cache.redis import make_cache_backend

from . import const


class LastFmAPIClient(CachedAPIClient):
    """
    Fetches listening history from Last.fm.

    Further reading:
      https://www.last.fm/api
    """

    provider_name = const.PROVIDER_NAME

    def __init__(self, api_key: str | None = None, **session_opts: Any) -> None:
        self._api_key = api_key or Settings.load().secrets.lastfm_key.get_secret_value()
        rate_limiter = rate_limits.shared(
            const.QUOTA_KEY,
            provider=LastFmAPIClient.provider_name,
            limits=const.RATE_LIMITS,
            concurrency=const.CONCURRENCY,
        )

        super().__init__(
            backend=make_cache_backend("lastfm_web_api"),
            expire_after=dt.timedelta(days=30),
            base_url="https://ws.audioscrobbler.com/2.0/",
            hooks=LoggingHook(provider=LastFmAPIClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            headers=provider_default_headers(),
            **session_opts,
        )

    async def user_top_tracks(
        self,
        username: str,
        *,
        period: str = "1month",
        limit: int = 50,
    ) -> niquests.Response:
        p = {
            "method": "user.getTopTracks",
            "format": "json",
            "api_key": self._api_key,
            "user": username,
            "period": period,
            "limit": str(limit),
        }
        return await self.get("/", params=p)

    async def user_recent_tracks(
        self,
        username: str,
        *,
        limit: int = 200,
    ) -> niquests.Response:
        p = {
            "method": "user.getRecentTracks",
            "format": "json",
            "api_key": self._api_key,
            "user": username,
            "limit": str(limit),
        }
        return await self.get("/", params=p)
