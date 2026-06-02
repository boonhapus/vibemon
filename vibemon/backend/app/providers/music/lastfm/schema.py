"""Last.fm Web API response schemas for listening history endpoints.

Further reading:
  https://www.last.fm/api
"""

from typing import Any

import pydantic

from . import validators


class _BaseModel(pydantic.BaseModel):
    """Shared Pydantic settings for Last.fm response models."""

    model_config = pydantic.ConfigDict(extra="ignore", populate_by_name=True)


class Artist(_BaseModel):
    """
    Nested ``artist`` object on a track entry.

    Last.fm may return a single object or a one-element list when multiple
    artists are credited; validators keep the primary artist only.

    Further reading:
      https://www.last.fm/api/show/user.getTopTracks
      https://www.last.fm/api/show/user.getRecentTracks
    """

    mbid: validators.MBID | None = None
    name: str = pydantic.Field(alias="#text")


class TrackAttrs(_BaseModel):
    """
    Track-level ``@attr`` metadata.

    ``rank`` appears on ``user.getTopTracks`` entries; ``nowplaying`` marks the
    live stream on ``user.getRecentTracks`` when the user is currently listening.

    Further reading:
      https://www.last.fm/api/show/user.getTopTracks
      https://www.last.fm/api/show/user.getRecentTracks
    """

    rank: int
    nowplaying: bool | None = None


class PageAttrs(_BaseModel):
    """
    Pagination and query metadata on a ``toptracks`` or ``recenttracks`` page.

    Further reading:
      https://www.last.fm/api/show/user.getTopTracks
      https://www.last.fm/api/show/user.getRecentTracks
    """

    user: str
    page: int
    per_page: int = pydantic.Field(alias="perPage")
    total: int
    total_pages: int = pydantic.Field(alias="totalPages")


class Track(_BaseModel):
    """
    One track entry from `user.getTopTracks` or `user.getRecentTracks`.

    Further reading:
      https://www.last.fm/api/show/user.getTopTracks
      https://www.last.fm/api/show/user.getRecentTracks
    """

    name: str
    mbid: validators.MBID | None = None
    playcount: int = 1
    duration: validators.Seconds | None = None
    artist: Artist
    attrs: TrackAttrs | None = pydantic.Field(default=None, alias="@attr")


class TracksPage(_BaseModel):
    """
    Parsed `page` object from `user.getTopTracks` or `user.getRecentTracks`.

    Further reading:
      https://www.last.fm/api/show/user.getTopTracks
      https://www.last.fm/api/show/user.getRecentTracks
    """

    track: list[Track] = pydantic.Field(default_factory=list)
    attrs: PageAttrs | None = pydantic.Field(default=None, alias="@attr")

    @pydantic.field_validator("track", mode="before")
    @classmethod
    def _normalize_tracks(cls, value: Any) -> list[Any]:
        if isinstance(value, dict):
            return [value]
        return value
