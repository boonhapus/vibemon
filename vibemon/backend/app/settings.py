"""Application configuration loaded from ``VIBEMON_*`` environment variables."""

from typing import Annotated, Any, ClassVar, Literal, Self
from urllib.parse import urlsplit
import pathlib

import pydantic
import pydantic_settings


def _validate_database_url(value: str) -> str:
    """Require an async SQLAlchemy URL for SQLite or PostgreSQL."""
    accepted_schemes = ("sqlite+aiosqlite", "postgresql+asyncpg")

    if not any(value.startswith(f"{scheme}://") for scheme in accepted_schemes):
        raise ValueError(f"database URL must start with sqlite+aiosqlite:// or postgresql+asyncpg://, got {value!r}")
    return value


def _validate_cache_url(value: str) -> str:
    """Accept Redis or a SQLite file URL for the HTTP response cache."""
    parts = urlsplit(value)

    if parts.scheme in ("redis", "rediss"):
        return value

    if parts.scheme == "sqlite" and parts.path:
        return value

    raise ValueError(f"cache URL must be redis://, rediss://, or sqlite:///path, got {value!r}")


def _validate_obstore_url(value: str) -> str:
    """Require a non-empty obstore-backed asset store URL."""
    accepted_schemes = ("file", "s3", "gs", "az", "memory", "http", "https")

    if not value:
        raise ValueError("assets URL must not be empty")

    parts = urlsplit(value)
    if parts.scheme not in accepted_schemes:
        raise ValueError(f"assets URL scheme must be one of {sorted(accepted_schemes)!r}, got {parts.scheme!r}")
    return value


def _validate_google_model_string(value: str) -> str:
    """Require a ``provider:model`` string for pydantic-ai Google models."""
    accepted_providers = ("google", "google-gla")

    provider, _, model = value.partition(":")

    if provider not in accepted_providers or not model:
        raise ValueError(f"model string must be 'google-gla:model_name' or 'google:model_name', got {value!r}")

    return value


type DatabaseUrl = Annotated[str, pydantic.AfterValidator(_validate_database_url)]
"""Validated async database connection URL."""

type CacheUrl = Annotated[str, pydantic.AfterValidator(_validate_cache_url)]
"""Validated HTTP cache backend URL (Redis or SQLite file)."""

type ObstoreUrl = Annotated[str, pydantic.AfterValidator(_validate_obstore_url)]
"""Validated obstore asset store URL."""

type GoogleModelString = Annotated[str, pydantic.AfterValidator(_validate_google_model_string)]
"""Validated ``google`` or ``google-gla`` model selector for GenAI."""

type EnvironmentT = Literal["dev", "test", "prod"]
"""Runtime environment name for local safety defaults."""


class ApiSecrets(pydantic.BaseModel):
    """Third-party API credentials and the app-owned trainer encryption key."""

    eleven_labs: pydantic.SecretStr
    google: pydantic.SecretStr
    lastfm_key: pydantic.SecretStr
    lastfm_secret: pydantic.SecretStr
    trainer_encryption: pydantic.SecretStr


class GenAiModels(pydantic.BaseModel):
    """Google text and image model selectors for asset generation."""

    text: GoogleModelString
    image: GoogleModelString
    fake_assets: bool = False
    """Use the offline ``FakeVibemonAssetGenerator`` instead of the Google client."""


class StorageUrls(pydantic.BaseModel):
    """Database, HTTP cache, and object-store connection URLs."""

    database: DatabaseUrl
    cache: CacheUrl
    assets: ObstoreUrl


class LastFmConfig(pydantic.BaseModel):
    """Last.fm OAuth callback used during account linking."""

    callback: pydantic.HttpUrl = pydantic.HttpUrl("http://127.0.0.1:8765/lastfm/callback")


class MusicBrainzConfig(pydantic.BaseModel):
    """MusicBrainz Web API endpoint (public API or self-hosted mirror)."""

    base_url: pydantic.HttpUrl = pydantic.HttpUrl("https://musicbrainz.org/ws/2/")

    @pydantic.model_validator(mode="after")
    def _path_ends_with_ws2(self) -> Self:
        path = urlsplit(str(self.base_url)).path.rstrip("/")
        if not path.endswith("/ws/2"):
            raise ValueError(f"MusicBrainz base URL path must end with /ws/2, got {path!r}")
        return self


class Settings(pydantic_settings.BaseSettings):
    """Root settings object; nested groups map to ``VIBEMON_<GROUP>__<FIELD>`` env keys."""

    _loaded: ClassVar[Settings | None] = None

    environment: EnvironmentT = "prod"
    secrets: ApiSecrets
    genai: GenAiModels
    storage: StorageUrls
    lastfm: LastFmConfig = LastFmConfig()
    musicbrainz: MusicBrainzConfig = MusicBrainzConfig()

    model_config = pydantic_settings.SettingsConfigDict(
        env_prefix="VIBEMON_",
        env_nested_delimiter="__",
        env_file=(
            ".env",
            "../.env",
            "../../.env",
            str(pathlib.Path(__file__).resolve().parents[3] / ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @classmethod
    def load(cls, *, refresh: bool = False, **overrides: Any) -> Settings:
        """Load settings from env files and the process environment.

        Returns a process-wide singleton. Pass ``refresh=True`` to re-read env
        files after tests mutate ``os.environ``. Override kwargs mirror nested
        groups, e.g. ``storage={"assets": "file:///tmp/monstore"}``.
        """
        if overrides:
            instance = cls()

            for key, patch in overrides.items():
                if key not in cls.model_fields:
                    raise ValueError(f"Unknown Settings group {key!r}")

                if not isinstance(patch, dict):
                    raise TypeError(f"Settings override {key!r} must be a dict of field updates")

                section = getattr(instance, key)
                instance = instance.model_copy(update={key: section.model_copy(update=patch)})

            cls._loaded = instance

        elif refresh or cls._loaded is None:
            cls._loaded = cls()

        return cls._loaded
