import pydantic_settings
import pydantic


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""
    weather_api_key: pydantic.SecretStr
    google_api_key: pydantic.SecretStr

    txt_ai_model: str = "gemini-flash-lite-latest"
    # img_ai_model: str = "gemini-3.1-flash-image-preview"
    img_ai_model: str = "gemini-2.5-flash-image"

    model_config = pydantic_settings.SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8")


settings = Settings()  # type: ignore
