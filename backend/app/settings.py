import pydantic_settings
import pydantic


class Settings(pydantic_settings.BaseSettings):
    """A collection for API keys."""

    eleven_labs_api_key: pydantic.SecretStr
    """https://elevenlabs.io/app/api/api-keys"""

    google_api_key: pydantic.SecretStr
    """"https://aistudio.google.com/projects"""

    weather_api_key: pydantic.SecretStr
    """https://www.weatherapi.com/my/"""

    txt_ai_model: str = "gemini-flash-lite-latest"
    img_ai_model: str = "gemini-2.5-flash-image"

    model_config = pydantic_settings.SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8")


settings = Settings()  # type: ignore
