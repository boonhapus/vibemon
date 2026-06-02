"""Shared VIBEMON_* environment values for backend tests."""

import pathlib

import pytest


def apply_test_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    database_url: str = "sqlite+aiosqlite:///:memory:",
    cache_url: str | None = None,
    tmp_path: pathlib.Path | None = None,
) -> None:
    resolved_cache = cache_url
    if resolved_cache is None:
        path = (tmp_path or pathlib.Path("/tmp/vibemon-test-cache")) / "api_cache.db"
        resolved_cache = f"sqlite:///{path.as_posix()}"

    monkeypatch.setenv("VIBEMON_SECRETS__ELEVEN_LABS", "test")
    monkeypatch.setenv("VIBEMON_ENVIRONMENT", "test")
    monkeypatch.setenv("VIBEMON_SECRETS__GOOGLE", "test")
    monkeypatch.setenv("VIBEMON_SECRETS__LASTFM_KEY", "test-api-key")
    monkeypatch.setenv("VIBEMON_SECRETS__LASTFM_SECRET", "test-api-secret")
    monkeypatch.setenv("VIBEMON_SECRETS__TRAINER_ENCRYPTION", "test-secrets-key")
    monkeypatch.setenv("VIBEMON_GENAI__TEXT", "google-gla:test")
    monkeypatch.setenv("VIBEMON_GENAI__IMAGE", "google-gla:test")
    monkeypatch.setenv("VIBEMON_STORAGE__DATABASE", database_url)
    monkeypatch.setenv("VIBEMON_STORAGE__CACHE", resolved_cache)
    monkeypatch.setenv("VIBEMON_STORAGE__ASSETS", "memory:///")
