"""Tests for MusicBrainz recording response schemas."""

from pathlib import Path
import json

from app.providers.music.musicbrainz import schema

# Full raw GET /recording/{mbid}?inc=isrcs+tags+genres+url-rels+artist-credits
# (Dua Lipa — Blow Your Mind (Mwah), MBID 026fa041-3917-4c73-9079-ed16e36f20f8).
# Loaded before ``Recording.model_validate`` so available fields stay visible here.
_RECORDING_LOOKUP_PAYLOAD = json.loads(
    Path(__file__).with_name("_recording_lookup_payload.json").read_text(encoding="utf-8")
)


def test_recordings_search_response_parses_search_payload() -> None:
    payload = {
        "created": "2026-05-30T02:48:40.523Z",
        "count": 18,
        "offset": 0,
        "recordings": [
            {
                "id": "026fa041-3917-4c73-9079-ed16e36f20f8",
                "score": 100,
                "title": "Blow Your Mind (Mwah)",
                "length": 178583,
                "artist-credit": [
                    {
                        "name": "Dua Lipa",
                        "artist": {
                            "id": "6f1a58bf-9b1b-49cf-a44a-6cefad7ae04f",
                            "name": "Dua Lipa",
                            "sort-name": "Lipa, Dua",
                        },
                    }
                ],
                "isrcs": ["GBAHT1600318"],
                "genres": [{"id": "911c7bbb-172d-4df8-9478-dbff4296e791", "name": "pop", "count": 5}],
                "tags": [{"count": 5, "name": "pop"}],
            }
        ],
    }

    assert payload["count"] == 18
    recordings = [schema.Recording.model_validate(t) for t in payload["recordings"]]

    assert len(recordings) == 1
    assert recordings[0].title == "Blow Your Mind (Mwah)"
    assert recordings[0].artist_credit[0].artist.name == "Dua Lipa"
    assert recordings[0].genres[0].name == "pop"
    assert recordings[0].tags[0].name == "pop"


def test_recording_parses_full_lookup_payload() -> None:
    payload = _RECORDING_LOOKUP_PAYLOAD

    assert payload["id"] == "026fa041-3917-4c73-9079-ed16e36f20f8"
    assert "genres" in payload
    assert "tags" in payload
    assert payload["genres"][0].keys() >= {"id", "name", "count", "disambiguation"}
    assert payload["tags"][0].keys() >= {"name", "count"}

    recording = schema.Recording.model_validate(payload)

    assert recording.id == "026fa041-3917-4c73-9079-ed16e36f20f8"
    assert recording.title == "Blow Your Mind (Mwah)"
    assert recording.length == 178.583
    assert recording.first_release_date == "2016-08-26"
    assert recording.disambiguation == "explicit"
    assert recording.video is False
    assert recording.isrcs == ["DEUM71601954", "GBAHT1600302", "GBAHT1600318"]
    assert [g.name for g in recording.genres] == [
        "contemporary r&b",
        "dance-pop",
        "electropop",
        "pop",
        "synth-pop",
    ]
    assert [t.name for t in recording.tags] == [
        "contemporary r&b",
        "dance-pop",
        "electropop",
        "pop",
        "sexy",
        "synth-pop",
    ]
    assert recording.genres[3].id == "911c7bbb-172d-4df8-9478-dbff4296e791"
    assert recording.relations[0].url is not None
    assert "open.spotify.com" in recording.relations[0].url.resource
