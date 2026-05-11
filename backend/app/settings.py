from typing import Self
from urllib.parse import urlsplit
import os
import pathlib

import pydantic_settings
import pydantic


_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""
    eleven_labs_api_key: pydantic.SecretStr = pydantic.Field(json_schema_extra={"mirror_to_os.environ": True})
    """https://elevenlabs.io/app/api/api-keys"""

    google_api_key: pydantic.SecretStr = pydantic.Field(json_schema_extra={"mirror_to_os.environ": True})
    """https://aistudio.google.com/api-keys"""

    openai_api_key: pydantic.SecretStr | None = pydantic.Field(None, json_schema_extra={"mirror_to_os.environ": True})
    """https://platform.openai.com/api-keys"""

    opencode_api_key: pydantic.SecretStr | None = pydantic.Field(None, json_schema_extra={"mirror_to_os.environ": True})
    """..."""

    # ── Specific models ───────────────────────────────────────────────────────────────

    txt_ai_model: str
    img_ai_model: str

    # ── Sprite storage ────────────────────────────────────────────────────────────────

    sprite_store_url: str = "file://./.generated/sprites"
    """
    Where sprite sheets get persisted. Any obstore-supported URL.

    Local: ``file://<path>`` (relative paths anchor at repo root).
    Remote: ``s3://bucket/prefix``, ``gs://bucket/prefix``, ``az://container/prefix``.
    Ephemeral: ``memory:///`` (tests).
    """

    # ── Configuration ─────────────────────────────────────────────────────────────────

    model_config = pydantic_settings.SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @pydantic.field_validator("txt_ai_model", "img_ai_model")
    @classmethod
    def _require_provider_prefix(cls, v: str) -> str:
        provider, _, model = v.partition(":")

        if not provider or not model:
            raise ValueError(f"model string must be 'provider:model_name', got {v!r}")

        return v

    @pydantic.field_validator("sprite_store_url")
    @classmethod
    def _anchor_local_store(cls, v: str) -> str:
        # Resolve relative file:// paths against the repo root and ensure the dir exists.
        parts = urlsplit(v)

        if parts.scheme != "file":
            return v

        # urlsplit on `file://./path` puts `.` in netloc; reattach if so.
        raw = (parts.netloc + parts.path) if parts.netloc not in ("", "localhost") else parts.path
        path = pathlib.Path(raw)

        if not path.is_absolute():
            path = (_REPO_ROOT / path).resolve()

        path.mkdir(parents=True, exist_ok=True)
        # RFC 8089 form: `file:///<absolute-path>` (empty authority, leading slash).
        return f"file:///{path.as_posix().lstrip('/')}"

    @pydantic.model_validator(mode="after")
    def export_to_environ(self) -> Self:
        """Sync loaded settings to os.environ for downstream libraries."""
        for name, field in Settings.model_fields.items():
            if field.json_schema_extra is None:
                continue
            if not isinstance(field.json_schema_extra, dict):
                continue
            if not field.json_schema_extra.get("mirror_to_os.environ"):
                continue

            val = getattr(self, name)

            if hasattr(val, "get_secret_value"):
                val = val.get_secret_value()

            if os.getenv(env_key := name.upper()) != str(val):
                os.environ[env_key] = str(val)

        return self


settings = Settings()  # type: ignore
