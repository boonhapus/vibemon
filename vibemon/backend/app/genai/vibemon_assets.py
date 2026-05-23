from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
import functools as ft
import re

from elevenlabs import AsyncElevenLabs
import pydantic_ai
import structlog

from app.genai import audio, image, prompts
from app.settings import get_settings

if TYPE_CHECKING:
    from app.domains.move import entity as move_entity
    from app.domains.vibemon import entity as vibemon_entity
    from app.domains.vibemon import identity as vibemon_identity

_LOGGER = structlog.get_logger(__name__)
RX_WORDS_ONLY = re.compile(r"[^\w-]")

type TextAgentFactory = Callable[[], Any]
type ImageAgentFactory = Callable[[], image.ImageAgent]
type ElevenLabsFactory = Callable[[], AsyncElevenLabs]


class VibemonAssetGenerator:
    def __init__(
        self,
        *,
        text_agent_factory: TextAgentFactory | None = None,
        image_agent_factory: ImageAgentFactory | None = None,
        elevenlabs_factory: ElevenLabsFactory | None = None,
    ) -> None:
        self._text_agent_factory = text_agent_factory or _default_text_agent
        self._image_agent_factory = image_agent_factory or _default_image_agent
        self._elevenlabs_factory = elevenlabs_factory or _default_elevenlabs
        self._text_agent: Any | None = None
        self._image_agent: image.ImageAgent | None = None
        self._elevenlabs: AsyncElevenLabs | None = None

    @property
    def _text_agent_client(self) -> Any:
        if self._text_agent is None:
            self._text_agent = self._text_agent_factory()
        return self._text_agent

    @property
    def _image_agent_client(self) -> image.ImageAgent:
        if self._image_agent is None:
            self._image_agent = self._image_agent_factory()
        return self._image_agent

    @property
    def _elevenlabs_client(self) -> AsyncElevenLabs:
        if self._elevenlabs is None:
            self._elevenlabs = self._elevenlabs_factory()
        return self._elevenlabs

    async def generate_name(
        self,
        identity: vibemon_identity.Identity,
        moves: list[move_entity.Move],
        visual_notes: str | None,
    ) -> str:
        prompt = prompts.render("species-name.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
        result = await self._text_agent_client.run(prompt.text)
        name = RX_WORDS_ONLY.sub(repl="", string=result.output)
        await _LOGGER.adebug(
            "Generated Vibemon name",
            name=name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
        )
        return name

    async def generate_reference_image(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        _require_aesthetic(vibemon)
        prompt = prompts.render("sprite-reference.mdc", vibemon=vibemon)
        result = await self._image_agent_client.run(prompt.text)
        output = cast(Any, result.output)
        await _LOGGER.adebug(
            "Generated Vibemon sprite reference",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
        )
        return output.data

    async def generate_sprite_sheet_image(self, vibemon: vibemon_entity.Vibemon, reference_image: bytes) -> bytes:
        _require_aesthetic(vibemon)
        prompt = prompts.render("sprite-sheet.mdc", vibemon=vibemon)
        result = await self._image_agent_client.run(
            [pydantic_ai.BinaryImage(data=reference_image, media_type="image/png"), prompt.text]
        )
        output = cast(Any, result.output)
        await _LOGGER.adebug(
            "Generated Vibemon sprite sheet",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
        )
        return output.data

    async def generate_battle_cry_audio(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        prompt = prompts.render("battle-cry.mdc", vibemon=vibemon)
        result = await self._text_agent_client.run(prompt.text, output_type=audio.VibemonSound)
        await _LOGGER.adebug(
            "Generated Vibemon battle cry",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            **result.output.model_dump(),
        )
        stream = self._elevenlabs_client.text_to_sound_effects.convert(
            text=result.output.description,
            duration_seconds=result.output.duration,
        )
        return b"".join([audio_chunk async for audio_chunk in stream])


@ft.cache
def get_default_asset_generator() -> VibemonAssetGenerator:
    return VibemonAssetGenerator()


def _require_aesthetic(vibemon: vibemon_entity.Vibemon) -> None:
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to generate sprite assets")


def _default_text_agent() -> Any:
    settings = get_settings()
    return pydantic_ai.Agent(settings.txt_ai_model)


def _default_image_agent() -> image.ImageAgent:
    settings = get_settings()
    return image.build_image_agent(settings.img_ai_model)


def _default_elevenlabs() -> AsyncElevenLabs:
    settings = get_settings()
    return AsyncElevenLabs(api_key=settings.eleven_labs_api_key.get_secret_value())
