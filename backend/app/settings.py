from typing import Self
import os

import pydantic_settings
import pydantic


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""

    eleven_labs_api_key: pydantic.SecretStr
    """https://elevenlabs.io/app/api/api-keys"""

    google_api_key: pydantic.SecretStr
    """https://aistudio.google.com/api-keys"""

    nvidia_api_key: pydantic.SecretStr | None = None
    """https://build.nvidia.com/settings/api-keys"""

    openai_api_key: pydantic.SecretStr | None = None
    """https://platform.openai.com/api-keys"""

    opencode_api_key: pydantic.SecretStr | None = None
    """..."""

    together_api_key: pydantic.SecretStr
    """https://api.together.ai/settings/profile"""

    weather_api_key: pydantic.SecretStr
    """https://www.weatherapi.com/my/"""

    # ── Specific models ───────────────────────────────────────────────────────────────

    txt_ai_model: str
    img_ai_model: str

    # ── Configuration ─────────────────────────────────────────────────────────────────

    model_config = pydantic_settings.SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8")

    @pydantic.field_validator("txt_ai_model", "img_ai_model")
    @classmethod
    def _require_provider_prefix(cls, v: str) -> str:
        provider, _, model = v.partition(":")

        if not provider or not model:
            raise ValueError(f"model string must be 'provider:model_name', got {v!r}")

        return v

    @pydantic.model_validator(mode="after")
    def export_to_environ(self) -> Self:
        for field_name, value in self:
            field_name = field_name.upper()

            if value is None or "API_KEY" not in field_name:
                continue

            os.environ[field_name] = value.get_secret_value() if isinstance(value, pydantic.SecretStr) else str(value)

        return self


settings = Settings()  # type: ignore
