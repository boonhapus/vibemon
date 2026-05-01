from typing import Self
import os

import pydantic_settings
import pydantic


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""
    headless: bool = False
    """Whether to generate the Aesthetic or not."""

    eleven_labs_api_key: pydantic.SecretStr = pydantic.Field(json_schema_extra={"mirror_to_os.environ": True})
    """https://elevenlabs.io/app/api/api-keys"""

    google_api_key: pydantic.SecretStr = pydantic.Field(json_schema_extra={"mirror_to_os.environ": True})
    """https://aistudio.google.com/api-keys"""

    nvidia_api_key: pydantic.SecretStr | None = pydantic.Field(None, json_schema_extra={"mirror_to_os.environ": True})
    """https://build.nvidia.com/settings/api-keys"""

    openai_api_key: pydantic.SecretStr | None = pydantic.Field(None, json_schema_extra={"mirror_to_os.environ": True})
    """https://platform.openai.com/api-keys"""

    opencode_api_key: pydantic.SecretStr | None = pydantic.Field(None, json_schema_extra={"mirror_to_os.environ": True})
    """..."""

    together_api_key: pydantic.SecretStr = pydantic.Field(json_schema_extra={"mirror_to_os.environ": True})
    """https://api.together.ai/settings/profile"""

    # ── Specific models ───────────────────────────────────────────────────────────────

    txt_ai_model: str
    img_ai_model: str

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
