"""MusicBrainz Web API response schemas for recording endpoints.

Further reading:
  https://musicbrainz.org/doc/MusicBrainz_API
  https://musicbrainz.org/doc/MusicBrainz_API/Search/RecordingSearch
"""

from urllib.parse import urlparse

import pydantic

from . import validators


class _BaseModel(pydantic.BaseModel):
    """Shared Pydantic settings for MusicBrainz response models."""

    model_config = pydantic.ConfigDict(extra="ignore", populate_by_name=True)


class Artist(_BaseModel):
    """Nested artist on an ``artist-credit`` entry."""

    id: str
    name: str
    sort_name: str | None = pydantic.Field(default=None, alias="sort-name")
    disambiguation: str = ""


class ArtistCredit(_BaseModel):
    """One credited artist (``artist-credit`` element)."""

    name: str
    joinphrase: str = ""
    artist: Artist


class UrlTarget(_BaseModel):
    id: str | None = None
    resource: str


class Relation(_BaseModel):
    """URL relationship; ``relations`` may include Spotify streaming links."""

    type: str | None = None
    type_id: str | None = pydantic.Field(default=None, alias="type-id")
    url: UrlTarget | None = None


class Tag(_BaseModel):
    name: str
    count: int | None = None


class Genre(_BaseModel):
    """Curated genre tag (``inc=genres``); includes MusicBrainz genre entity id."""

    id: str
    name: str
    count: int | None = None
    disambiguation: str = ""


class Recording(_BaseModel):
    """
    One recording from lookup-by-MBID or from search results.

    Path lookup (``GET /recording/{mbid}``) returns these fields at the top level.
    Search wraps hits in a ``recordings`` list.
    """

    id: str
    title: str
    length: validators.Seconds | None = None
    disambiguation: str = ""
    video: bool | None = None
    first_release_date: str | None = pydantic.Field(default=None, alias="first-release-date")
    isrcs: list[str] = pydantic.Field(default_factory=list)
    genres: list[Genre] = pydantic.Field(default_factory=list)
    tags: list[Tag] = pydantic.Field(default_factory=list)
    relations: list[Relation] = pydantic.Field(default_factory=list)
    artist_credit: list[ArtistCredit] = pydantic.Field(default_factory=list, alias="artist-credit")

    @property
    def first_spotify_id(self) -> str | None:
        """Extract the Spotify ID."""
        if not self.relations:
            return None

        for relation in self.relations:
            if relation.url is not None and "open.spotify.com/track" in relation.url.resource:
                return urlparse(relation.url.resource).path.rsplit("/", 1)[-1]

        return None
