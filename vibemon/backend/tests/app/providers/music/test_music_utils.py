"""Tests for music provider search ranking helpers."""

from app.providers.music.lastfm import schema as lastfm_schema
from app.providers.music.musicbrainz import schema as mb_schema
from app.providers.music.utils import candidate_ranking


def _lastfm_track(**overrides: object) -> lastfm_schema.Track:
    payload: dict[str, object] = {
        "name": "Mr. Brightside",
        "duration": "223000",
        "playcount": "4",
        "artist": {"name": "The Killers"},
    }
    payload.update(overrides)
    return lastfm_schema.Track.model_validate(payload)


def _recording(**overrides: object) -> mb_schema.Recording:
    payload: dict[str, object] = {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": "Mr. Brightside",
        "length": 223_000,
        "disambiguation": "",
        "isrcs": [],
        "artist-credit": [
            {
                "name": "The Killers",
                "artist": {"id": "aaaa", "name": "The Killers"},
            }
        ],
    }
    payload.update(overrides)
    return mb_schema.Recording.model_validate(payload)


def test_candidate_ranking_prefers_studio_over_live() -> None:
    track = _lastfm_track()
    studio = _recording(id="studio-mbid", isrcs=["GBUM70300485"])
    live = _recording(
        id="live-mbid",
        disambiguation="live, 2009-07: Royal Albert Hall, London, UK",
    )

    _, studio_score = candidate_ranking(studio, track=track)
    _, live_score = candidate_ranking(live, track=track)

    assert studio_score > live_score


def test_candidate_ranking_prefers_isrc_when_similarity_matches() -> None:
    track = _lastfm_track()
    with_isrc = _recording(id="with-isrc", isrcs=["GBUM70300485"])
    without_isrc = _recording(id="without-isrc", isrcs=[])

    _, with_score = candidate_ranking(with_isrc, track=track)
    _, without_score = candidate_ranking(without_isrc, track=track)

    assert with_score > without_score
