from typing import Annotated, Self
import os

import pydantic_settings
import pydantic

type MirrorToEnv[T] = Annotated[T, "MIRROR_TO_OS.ENVIRON"]


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""

    eleven_labs_api_key: MirrorToEnv[pydantic.SecretStr]
    """https://elevenlabs.io/app/api/api-keys"""

    google_api_key: MirrorToEnv[pydantic.SecretStr]
    """https://aistudio.google.com/api-keys"""

    nvidia_api_key: MirrorToEnv[pydantic.SecretStr | None] = None
    """https://build.nvidia.com/settings/api-keys"""

    openai_api_key: MirrorToEnv[pydantic.SecretStr | None] = None
    """https://platform.openai.com/api-keys"""

    opencode_api_key: MirrorToEnv[pydantic.SecretStr | None] = None
    """..."""

    together_api_key: MirrorToEnv[pydantic.SecretStr]
    """https://api.together.ai/settings/profile"""

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
        """Sync loaded settings to os.environ for downstream libraries."""
        for name, field in self.model_fields.items():
            if any(m == "MIRROR_TO_OS.ENVIRON" for m in field.metadata):
                if (val := getattr(self, name)) is None:
                    continue

                if hasattr(val, "get_secret_value"):
                    val = val.get_secret_value()

                # Set the environment variable
                os.environ[name.upper()] = str(val)

        return self


settings = Settings()  # type: ignore
