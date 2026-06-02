"""ReccoBeats API response schemas for audio-features endpoints.

Further reading:
  https://reccobeats.com/docs/apis/get-audio-features
  https://reccobeats.com/docs/apis/get-track-audio-features
  https://reccobeats.com/docs/documentation/Analysis/audio-features-extraction
"""

from urllib.parse import urlparse

import pydantic


class _BaseModel(pydantic.BaseModel):
    """Shared Pydantic settings for ReccoBeats response models."""

    model_config = pydantic.ConfigDict(extra="ignore", populate_by_name=True)


class AudioFeatures(_BaseModel):
    """
    Audio analysis for one track.

    Returned at the top level by ``GET /v1/track/{id}/audio-features`` and as
    elements of ``content`` from ``GET /v1/audio-features``.
    """

    id: str | None = None
    href: str | None = None
    isrc: str | None = None
    acousticness: float
    danceability: float
    energy: float
    instrumentalness: float
    key: int | None = None
    key_mode: str | None = None
    key_name: str | None = None
    liveness: float
    loudness: float
    mode: int
    mode_name: str | None = None
    speechiness: float
    tempo: float
    valence: float

    @property
    def spotify_id(self) -> str | None:
        """Extract the Spotify track ID from ``href`` when present."""
        if self.href and "open.spotify.com" in self.href:
            return urlparse(self.href).path.rsplit("/", 1)[-1]
        return None
