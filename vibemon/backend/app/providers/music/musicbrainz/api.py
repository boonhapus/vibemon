"""MusicBrainz Web API client for the music provider."""

from typing import Any
import datetime as dt

import niquests

from app.providers._api.hooks import LoggingHook, RateLimiterHook, ThrottledSessionMixin
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.providers._api.session import CachedAPIClient
from app.settings import Settings
from app.storage.cache.redis import make_cache_backend

from . import utils


class MusicBrainzAPIClient(ThrottledSessionMixin, CachedAPIClient):
    """
    Fetches recording and artist metadata from MusicBrainz.

    Further reading:
      https://musicbrainz.org/doc/MusicBrainz_API
    """

    provider_name = "musicbrainz.web_api"

    def __init__(self, **session_opts: Any) -> None:
        settings = Settings.load()

        # DEV NOTE: @boonhapus, 2026/05/31
        # The local Musicbrainz server is HTTP/1.1, so we enforce "no multiplexing".
        selfhost_concurrency = 1 if settings.environment == "dev" else None

        rate_limiter = RateLimiterHook(
            (25, dt.timedelta(seconds=1)),
            provider=MusicBrainzAPIClient.provider_name,
            concurrency=2 if "musicbrainz.org" in str(settings.musicbrainz.base_url) else selfhost_concurrency,
        )

        super().__init__(
            backend=make_cache_backend("musicbrainz_web_api"),
            expire_after=dt.timedelta(days=30),
            base_url=str(settings.musicbrainz.base_url),
            hooks=LoggingHook(provider=MusicBrainzAPIClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            headers=provider_default_headers(),
            **session_opts,
        )

    async def search_recording(
        self,
        recording: str,
        artist_name: str | None = None,
        artist_mbid: str | None = None,
        limit: int = 5,
    ) -> niquests.Response:
        """Look up a single recording by Title and Artist."""
        q = {"recording": recording}

        if artist_mbid is not None:
            q["arid"] = artist_mbid
        elif artist_name is not None:
            q["artist"] = artist_name

        p = {
            "query": utils.build_simple_lucene_query(q),
            "limit": str(limit),
            "inc": "isrcs+tags+genres+url-rels+artist-credits",
        }
        r = await self.get("/recording", params=p)
        return r

    async def recording(self, mbid: str) -> niquests.Response:
        """Look up a recording by MusicBrainz ID."""
        p = {"inc": "isrcs+tags+genres+url-rels+artist-credits"}
        r = await self.get(f"/recording/{mbid}", params=p)
        return r
