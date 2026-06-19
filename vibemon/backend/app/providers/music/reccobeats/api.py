"""ReccoBeats audio analysis client for the music provider."""

from typing import Any
import datetime as dt

import niquests

from app.providers._api import rate_limits
from app.providers._api.hooks import LoggingHook
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.providers._api.session import CachedAPIClient
from app.storage.cache.redis import make_cache_backend

from . import const


class ReccoBeatsAPIClient(CachedAPIClient):
    """
    Fetches audio analysis keyed by ISRC or Spotify track ID.

    Community rebuild of Spotify's deprecated audio-features endpoint.
    """

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = rate_limits.shared(
            const.QUOTA_KEY,
            provider=ReccoBeatsAPIClient.provider_name,
            limits=const.RATE_LIMITS,
        )

        super().__init__(
            backend=make_cache_backend("reccobeats_web_api"),
            expire_after=dt.timedelta(days=30),
            base_url="https://api.reccobeats.com/",
            hooks=LoggingHook(provider=ReccoBeatsAPIClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            headers=provider_default_headers(),
            **session_opts,
        )

    async def audio_features(self, *ids: str) -> niquests.Response:
        """Fetch audio features for Spotify track IDs and/or ISRCs (batched)."""
        p = {"ids": list(ids)}
        r = await self.get("v1/audio-features", params=p)
        return r
