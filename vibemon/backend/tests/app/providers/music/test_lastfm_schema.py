"""Tests for Last.fm listening-history response schemas."""

from app.providers.music.lastfm import schema as lastfm_schema


def test_tracks_page_normalizes_single_track_object() -> None:
    parsed = lastfm_schema.TracksPage.model_validate(
        {
            "@attr": {"user": "trainer-one", "page": "1", "perPage": "50", "total": "1", "totalPages": "1"},
            "track": {
                "name": "Metal Storm",
                "mbid": "11111111-1111-1111-1111-111111111111",
                "duration": "240",
                "playcount": "42",
                "artist": {
                    "name": "Steel Horizon",
                    "mbid": "22222222-2222-2222-2222-222222222222",
                },
            },
        }
    )

    assert len(parsed.track) == 1
    track = parsed.track[0]
    assert track.name == "Metal Storm"
    assert track.mbid == "11111111-1111-1111-1111-111111111111"
    assert track.duration == 240
    assert track.playcount == 42
    assert track.artist.name == "Steel Horizon"
    assert parsed.attrs is not None
    assert parsed.attrs.user == "trainer-one"
    assert parsed.attrs.page == 1


def test_tracks_page_accepts_empty_track_list() -> None:
    parsed = lastfm_schema.TracksPage.model_validate({"track": []})
    assert parsed.track == []


def test_tracks_page_treats_blank_mbids_as_none() -> None:
    parsed = lastfm_schema.TracksPage.model_validate(
        {
            "track": [
                {
                    "name": "Untagged",
                    "mbid": "",
                    "duration": "240000",
                    "artist": {"name": "Anonymous", "mbid": ""},
                }
            ]
        }
    )
    track = parsed.track[0]
    assert track.mbid is None
    assert track.artist.mbid is None
