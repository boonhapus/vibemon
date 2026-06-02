"""Unit tests for music provider response validators."""

from app.providers.music.lastfm import validators as lastfm_validators


def test_ensure_valid_duration_from_seconds() -> None:
    assert lastfm_validators.ensure_valid_duration(240) == 240


def test_ensure_valid_duration_from_milliseconds() -> None:
    assert lastfm_validators.ensure_valid_duration(240_000) == 240
