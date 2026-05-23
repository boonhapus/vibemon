from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast
import functools as ft
import re

from elevenlabs import AsyncElevenLabs
import pydantic_ai
import structlog

from app.genai import _image, sprites, structured_output, utils
from app.settings import get_settings

if TYPE_CHECKING:
    from app.domains.move import entity as move_entity
    from app.domains.vibemon import entity as vibemon_entity
    from app.domains.vibemon import identity as vibemon_identity

_LOGGER = structlog.get_logger(__name__)
RX_WORDS_ONLY = re.compile(r"[^\w-]")

type TxtAgentFactory = Callable[[], Any]
type ImgAgentFactory = Callable[[], Any]
type ElevenLabsFactory = Callable[[], AsyncElevenLabs]


class GenAIClient:
    def __init__(
        self,
        *,
        txt_agent_factory: TxtAgentFactory | None = None,
        img_agent_factory: ImgAgentFactory | None = None,
        elevenlabs_factory: ElevenLabsFactory | None = None,
    ) -> None:
        self._txt_agent_factory = txt_agent_factory or _default_txt_agent
        self._img_agent_factory = img_agent_factory or _default_img_agent
        self._elevenlabs_factory = elevenlabs_factory or _default_elevenlabs
        self._txt_agent: Any | None = None
        self._img_agent: Any | None = None
        self._elevenlabs: AsyncElevenLabs | None = None

    @property
    def txt_agent(self) -> Any:
        if self._txt_agent is None:
            self._txt_agent = self._txt_agent_factory()
        return self._txt_agent

    @property
    def img_agent(self) -> Any:
        if self._img_agent is None:
            self._img_agent = self._img_agent_factory()
        return self._img_agent

    @property
    def elevenlabs(self) -> AsyncElevenLabs:
        if self._elevenlabs is None:
            self._elevenlabs = self._elevenlabs_factory()
        return self._elevenlabs

    async def generate_vibemon_name(
        self,
        identity: vibemon_identity.Identity,
        moves: list[move_entity.Move],
        visual_notes: str | None,
    ) -> str:
        p = utils.load_prompt("species-name.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
        r = await self.txt_agent.run(p)
        d = RX_WORDS_ONLY.sub(repl="", string=r.output)
        await _LOGGER.adebug("Generate :: Vibemon name", name=d, prompt=p)
        return d

    async def generate_sprite_reference(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        if vibemon.aesthetic is None:
            raise ValueError("Vibemon aesthetic is required to generate sprite assets")
        p = utils.load_prompt("sprite-reference.mdc", vibemon=vibemon)
        r = await self.img_agent.run(p)
        output = cast(Any, r.output)
        await _LOGGER.adebug("Generate :: Vibemon sprite reference", vibemon=vibemon.name, prompt=p)
        return sprites.normalize_sprite_matte(
            output.data,
            bg_color=vibemon.aesthetic.background_color,
            rows=1,
            cols=1,
        )

    async def generate_sprite_sheet(self, vibemon: vibemon_entity.Vibemon, reference: bytes) -> bytes:
        if vibemon.aesthetic is None:
            raise ValueError("Vibemon aesthetic is required to generate sprite assets")
        p = utils.load_prompt("sprite-sheet.mdc", vibemon=vibemon)
        r = await self.img_agent.run([pydantic_ai.BinaryImage(data=reference, media_type="image/png"), p])
        output = cast(Any, r.output)
        d = sprites.normalize_sprite_matte(output.data, bg_color=vibemon.aesthetic.background_color)
        if issues := sprites.validate_sprite_sheet(d):
            raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")
        return d

    async def generate_battle_cry(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        p = utils.load_prompt("battle-cry.mdc", vibemon=vibemon)
        r = await self.txt_agent.run(p, output_type=structured_output.VibemonSound)
        await _LOGGER.adebug("Generate :: Vibemon battle cry", vibemon=vibemon.name, **r.output.model_dump())
        stream = self.elevenlabs.text_to_sound_effects.convert(
            text=r.output.description,
            duration_seconds=r.output.duration,
        )
        return b"".join([audio_chunk async for audio_chunk in stream])


@ft.cache
def get_default_client() -> GenAIClient:
    return GenAIClient()


def _default_txt_agent() -> Any:
    settings = get_settings()
    return pydantic_ai.Agent(settings.txt_ai_model)


def _default_img_agent() -> Any:
    settings = get_settings()
    return _image.build_image_agent(settings.img_ai_model)


def _default_elevenlabs() -> AsyncElevenLabs:
    settings = get_settings()
    return AsyncElevenLabs(api_key=settings.eleven_labs_api_key.get_secret_value())
