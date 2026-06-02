"""Tests for MusicBrainz Lucene query helpers."""

from app.providers.music.musicbrainz import utils


def test_build_simple_lucene_query_recording_and_artist() -> None:
    query = utils.build_simple_lucene_query(
        {"recording": "Bohemian Rhapsody", "artist": "Queen"},
    )
    assert query == 'recording:"Bohemian Rhapsody" AND artist:"Queen"'


def test_build_simple_lucene_query_escapes_quotes_and_backslashes() -> None:
    query = utils.build_simple_lucene_query(
        {"recording": r'He said "hello"', "artist": r"AC\DC"},
    )
    assert query == r'recording:"He said \"hello\"" AND artist:"AC\\DC"'


def test_build_simple_lucene_query_skips_empty_and_none_values() -> None:
    query = utils.build_simple_lucene_query(
        {"recording": "It's Only Love", "artist": None, "release": ""},
    )
    assert query == 'recording:"It\'s Only Love"'


def test_build_simple_lucene_query_returns_empty_string_without_fields() -> None:
    assert utils.build_simple_lucene_query({}) == ""
    assert utils.build_simple_lucene_query({"artist": None}) == ""
