"""Climate provider fetch/synthesize payload."""

from typing import Any

from app.providers import schema as providers_schema


class ClimatePayload(providers_schema.ProviderPayload):
    start_date: str
    end_date: str
    weather_augmented: dict[str, Any]
