import pydantic

from app.providers import schema as providers_schema

from .lastfm import schema as lastfm_schema
from .lastfm.validators import Seconds
from .musicbrainz import schema as mb_schema
from .reccobeats.validators import IsMajor


class TrackInfo(pydantic.BaseModel):
    """MusicBrainz-enriched Last.fm track metadata before audio features attach."""

    model_config = pydantic.ConfigDict(extra="forbid", populate_by_name=True)

    mbid: str
    isrc: str | None = None
    spotify_id: str | None
    name: str
    artist: str
    genres: list[str] = pydantic.Field(default_factory=list)
    tags: list[str] = pydantic.Field(default_factory=list)
    duration: Seconds
    plays: int = 1

    @classmethod
    def combine(cls, recording: mb_schema.Recording, track: lastfm_schema.Track) -> TrackInfo:
        """Mix a Musicbeatz recording and LastFM track."""
        return cls.model_validate(
            {
                "mbid": recording.id,
                "isrc": (recording.isrcs or [None])[0],
                "spotify_id": recording.first_spotify_id,
                "name": track.name,
                "artist": track.artist.name,
                "genres": [g.name for g in recording.genres],
                "tags": [t.name for t in recording.tags],
                "duration": track.duration or recording.length,
                "plays": track.playcount,
            }
        )


class Track(TrackInfo):
    """Resolved track with ReccoBeats audio features."""

    acousticness: float
    danceability: float
    energy: float
    instrumentalness: float
    liveness: float
    loudness: float
    is_major_key: IsMajor = pydantic.Field(alias="mode")
    speechiness: float
    tempo: float
    valence: float


class MusicPayload(providers_schema.ProviderPayload):
    """Captured Last.fm + MusicBrainz + ReccoBeats birth payload."""

    tracks: tuple[Track, ...]
    last7d: int
    last1m: int
