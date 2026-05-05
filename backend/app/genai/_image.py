# app/genai/image.py
from typing import Any, Protocol
import base64 as b64
import dataclasses

import niquests
import pydantic_ai

from app.settings import settings


@dataclasses.dataclass(frozen=True, slots=True)
class ImageRunResult:
    """Mirrors the shape of pydantic_ai.AgentRunResult, narrowed to images."""
    output: pydantic_ai.BinaryImage


class ImageAgent(Protocol):
    async def run(
        self,
        user_prompt: str,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> ImageRunResult: ...


class _GeminiImageAgent:
    """Thin wrapper over a real pydantic_ai.Agent for Gemini's image models."""

    def __init__(self, *, api_key: str, model: str):
        from pydantic_ai.models.google import GoogleModel
        from pydantic_ai.providers.google import GoogleProvider

        self._agent = pydantic_ai.Agent(GoogleModel(model, provider=GoogleProvider(api_key=api_key)))

    async def run(
        self,
        user_prompt: str,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> ImageRunResult:
        result = await self._agent.run(
            user_prompt,
            output_type=output_type,
            builtin_tools=builtin_tools or [pydantic_ai.ImageGenerationTool(size="2K")],
        )

        return ImageRunResult(output=result.output)


class _OpenAICompatibleImageAgent:
    """Calls /v1/images/generations on Together, OpenRouter, OpenAI, etc."""

    def __init__(self, *, api_key: str, base_url: str, model: str, **request_defaults: Any):
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._request_defaults = request_defaults

    async def run(
        self,
        user_prompt: str,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> ImageRunResult:
        # output_type / builtin_tools are accepted for API parity but ignored:
        # /v1/images/generations always returns image bytes, no agent loop.
        del output_type, builtin_tools

        response = await self._client.images.generate(
            model=self._model,
            prompt=user_prompt,
            n=1,
            **self._request_defaults,
        )

        item = response.data[0]

        if item.b64_json:
            data = b64.b64decode(item.b64_json)

        # Some providers ignore response_format and return a URL anyway.
        elif item.url:
            async with niquests.AsyncSession() as http:
                r = await http.get(item.url)
                r.raise_for_status()
                data = r.content

        else:
            raise RuntimeError("Image response had neither b64_json nor url")

        return ImageRunResult(output=pydantic_ai.BinaryImage(data=data, media_type="image/png"))


def build_image_agent(model_string: str) -> ImageAgent:
    """Build an image agent from a 'provider:model' string."""
    provider, _, model = model_string.partition(":")

    match provider:
        
        case "google-gla" | "google":
            if settings.google_api_key is None:
                raise ValueError("google_api_key required for google: models")

            return _GeminiImageAgent(
                api_key=settings.google_api_key.get_secret_value(),
                model=model,
            )

        case "openai":
            if settings.openai_api_key is None:
                raise ValueError("openai_api_key required for openai: models")

            return _OpenAICompatibleImageAgent(
                api_key=settings.openai_api_key.get_secret_value(),
                base_url="https://api.openai.com/v1",
                model=model,
                quality="high",
                extra_body={"output_format": "png"},
            )

        case "opencode":
            if settings.opencode_api_key is None:
                raise ValueError("opencode_api_key required for opencode: models")
            
            return _OpenAICompatibleImageAgent(
                api_key=settings.opencode_api_key.get_secret_value(),
                base_url="https://api.opencode.ai/v1",
                model=model,
                response_format="b64_json",
            )

        case _:
            raise ValueError(f"Unknown image provider prefix: {provider!r}")
