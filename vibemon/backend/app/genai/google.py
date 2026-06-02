"""Google GenAI agent builders for text and image generation."""

from collections.abc import Sequence
from typing import Any, Protocol
import dataclasses

import pydantic_ai

from app.settings import ApiSecrets

_GOOGLE_PROVIDERS = frozenset({"google-gla", "google"})


def parse_google_model(model_string: str) -> tuple[str, str]:
    """Split a ``provider:model`` string and validate the provider."""
    provider, _, model = model_string.partition(":")

    if provider not in _GOOGLE_PROVIDERS or not model:
        raise ValueError(f"model string must be 'google-gla:model_name' or 'google:model_name', got {model_string!r}")

    return provider, model


def build_text_agent(model_string: str, secrets: ApiSecrets) -> Any:
    """Build a pydantic-ai text agent for a Google model string."""
    _, model = parse_google_model(model_string)

    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider

    return pydantic_ai.Agent(GoogleModel(model, provider=GoogleProvider(api_key=secrets.google.get_secret_value())))


@dataclasses.dataclass(frozen=True, slots=True)
class ImageRunResult:
    """Narrow view of a pydantic-ai image run result."""

    output: pydantic_ai.BinaryImage


type ImagePrompt = str | Sequence[pydantic_ai.UserContent]


class ImageAgent(Protocol):
    """Minimal image-generation client surface used by asset workflows."""

    supports_image_inputs: bool

    async def run(
        self,
        user_prompt: ImagePrompt,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> ImageRunResult: ...


class GeminiImageAgent:
    """Gemini image agent with a fixed default generation tool configuration."""

    supports_image_inputs = True

    def __init__(self, *, api_key: str, model: str) -> None:
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        self._agent = pydantic_ai.Agent(GoogleModel(model, provider=GoogleProvider(api_key=api_key)))

    async def run(
        self,
        user_prompt: ImagePrompt,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> ImageRunResult:
        result = await self._agent.run(
            user_prompt,
            output_type=output_type,
            builtin_tools=builtin_tools or [pydantic_ai.ImageGenerationTool(size="2K", aspect_ratio="1:1")],
        )

        return ImageRunResult(output=result.output)


def build_image_agent(model_string: str, secrets: ApiSecrets) -> ImageAgent:
    """Build a Gemini image agent for a Google model string."""
    _, model = parse_google_model(model_string)

    return GeminiImageAgent(
        api_key=secrets.google.get_secret_value(),
        model=model,
    )
