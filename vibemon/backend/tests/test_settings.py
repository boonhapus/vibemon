import pydantic
import pytest

from app.settings import GenAiModels, LastFmConfig, MusicBrainzConfig, Settings, StorageUrls


def test_lastfm_callback_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    monkeypatch.delenv("VIBEMON_LASTFM__CALLBACK", raising=False)
    Settings.load(refresh=True)

    assert str(Settings.load().lastfm.callback) == "http://127.0.0.1:8765/lastfm/callback"


def test_storage_urls_reject_invalid_database_url() -> None:
    with pytest.raises(pydantic.ValidationError, match="database URL"):
        StorageUrls.model_validate(
            {
                "database": "postgres://localhost/vibemon",
                "cache": "sqlite:///tmp/cache.db",
                "assets": "memory:///",
            }
        )


def test_storage_urls_reject_invalid_cache_url() -> None:
    with pytest.raises(pydantic.ValidationError, match="cache URL"):
        StorageUrls.model_validate(
            {
                "database": "sqlite+aiosqlite:///:memory:",
                "cache": "memcached://localhost",
                "assets": "memory:///",
            }
        )


def test_storage_urls_reject_invalid_assets_scheme() -> None:
    with pytest.raises(pydantic.ValidationError, match="assets URL scheme"):
        StorageUrls.model_validate(
            {
                "database": "sqlite+aiosqlite:///:memory:",
                "cache": "sqlite:///tmp/cache.db",
                "assets": "ftp://example.test/bucket",
            }
        )


def test_genai_models_reject_non_google_provider() -> None:
    with pytest.raises(pydantic.ValidationError, match="google-gla:model_name"):
        GenAiModels.model_validate({"text": "openai:gpt-4o-mini", "image": "google-gla:test"})


def test_lastfm_config_accepts_http_callback() -> None:
    config = LastFmConfig.model_validate({"callback": "http://127.0.0.1:8765/lastfm/callback"})
    assert str(config.callback) == "http://127.0.0.1:8765/lastfm/callback"


def test_musicbrainz_base_url_defaults_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    monkeypatch.setenv("VIBEMON_MUSICBRAINZ__BASE_URL", "https://musicbrainz.org/ws/2/")
    Settings.load(refresh=True)

    assert str(Settings.load().musicbrainz.base_url) == "https://musicbrainz.org/ws/2/"


def test_environment_defaults_to_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    monkeypatch.setenv("VIBEMON_ENVIRONMENT", "prod")
    Settings.load(refresh=True)

    assert Settings.load().environment == "prod"


def test_environment_accepts_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    monkeypatch.setenv("VIBEMON_ENVIRONMENT", "dev")
    Settings.load(refresh=True)

    assert Settings.load().environment == "dev"


def test_musicbrainz_config_accepts_mirror_base_url() -> None:
    config = MusicBrainzConfig.model_validate({"base_url": "http://192.168.1.10:5000/ws/2/"})
    assert str(config.base_url) == "http://192.168.1.10:5000/ws/2/"


def test_musicbrainz_config_rejects_non_ws2_path() -> None:
    with pytest.raises(pydantic.ValidationError, match="/ws/2"):
        MusicBrainzConfig.model_validate({"base_url": "http://192.168.1.10:5000/ws/1/"})


def test_storage_urls_require_all_fields() -> None:
    with pytest.raises(pydantic.ValidationError):
        StorageUrls.model_validate(
            {
                "database": "sqlite+aiosqlite:///:memory:",
                "cache": "sqlite:///tmp/cache.db",
            }
        )


def test_load_applies_group_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.settings_env import apply_test_settings

    apply_test_settings(monkeypatch)
    Settings.load(storage={"assets": "memory:///override"})

    assert Settings.load().storage.assets == "memory:///override"


def test_load_rejects_unknown_group() -> None:
    with pytest.raises(ValueError, match="Unknown Settings group"):
        Settings.load(database={"url": "sqlite+aiosqlite:///:memory:"})


def test_load_rejects_non_dict_group_override() -> None:
    with pytest.raises(TypeError, match="must be a dict"):
        Settings.load(storage="memory:///")
