"""Orchestrate GenAI calls that produce Vibemon names, sprites, and battle cries."""

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any
import functools as ft
import io
import re

from elevenlabs import AsyncElevenLabs
from PIL import Image
import pydantic
import pydantic_ai
import structlog

from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets
from app.domains.vibemon import brand
from app.genai import google, prompts, sprite_facing, style_bible
from app.settings import Settings

if TYPE_CHECKING:
    from app.domains.move import entity as move_entity
    from app.domains.vibemon import entity as vibemon_entity
    from app.domains.vibemon import identity as vibemon_identity

_LOGGER = structlog.get_logger(__name__)
_RX_WORDS_ONLY = re.compile(r"[^\w-]")
REFERENCE_LIKENESS_MEDIA = frozenset({"image/png", "image/jpeg", "image/webp"})
_REFERENCE_MAX_BYTES = 10 * 1024 * 1024


class VibemonSound(pydantic.BaseModel):
    """Structured battle-cry brief passed to ElevenLabs sound generation."""

    description: str = pydantic.Field(description="Cinematic sound effect description.")
    duration: float = pydantic.Field(ge=0.5, le=4.0)


type TextAgentFactory = Callable[[], Any]
type ImageAgentFactory = Callable[[], google.ImageAgent]
type ElevenLabsFactory = Callable[[], AsyncElevenLabs]


class VibemonAssetGenerator:
    """Generate names, sprite assets, and battle-cry audio for one Vibemon."""

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
        self._image_agent: google.ImageAgent | None = None
        self._elevenlabs: AsyncElevenLabs | None = None

    def _text_agent_client(self) -> Any:
        if self._text_agent is None:
            self._text_agent = self._text_agent_factory()
        return self._text_agent

    def _image_agent_client(self) -> google.ImageAgent:
        if self._image_agent is None:
            self._image_agent = self._image_agent_factory()
        return self._image_agent

    def _elevenlabs_client(self) -> AsyncElevenLabs:
        if self._elevenlabs is None:
            self._elevenlabs = self._elevenlabs_factory()
        return self._elevenlabs

    async def generate_name(
        self,
        identity: vibemon_identity.Identity,
        moves: Sequence[move_entity.Move],
        visual_notes: str | None,
    ) -> str:
        prompt = prompts.render("species-name.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
        result = await self._text_agent_client().run(prompt.text)
        name = _RX_WORDS_ONLY.sub(repl="", string=result.output)
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
        style_refs: Sequence[pydantic_ai.UserContent] = [
            pydantic_ai.BinaryImage(data=style_bible.load_trainer_style_bible_png(), media_type="image/png"),
            pydantic_ai.BinaryImage(data=style_bible.load_hatchling_style_bible_png(), media_type="image/png"),
            prompt.text,
        ]
        result = await self._image_agent_client().run(style_refs)
        await _LOGGER.adebug(
            "Generated Vibemon sprite reference",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
        )
        return result.output.data

    async def generate_sprite_sheet_image(self, vibemon: vibemon_entity.Vibemon, reference_image: bytes) -> bytes:
        _require_aesthetic(vibemon)
        prompt = prompts.render("sprite-sheet.mdc", vibemon=vibemon)
        result = await self._image_agent_client().run(
            [pydantic_ai.BinaryImage(data=reference_image, media_type="image/png"), prompt.text]
        )
        await _LOGGER.adebug(
            "Generated Vibemon sprite sheet",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
        )
        return result.output.data

    async def generate_trainer_reference(
        self,
        likeness_bytes: bytes,
        *,
        username: str,
        likeness_media_type: str,
    ) -> tuple[bytes, brand.Color]:
        validate_reference_likeness(likeness_bytes, media_type=likeness_media_type)
        background_color = trainer_assets.solve_trainer_reference_background(likeness_bytes)
        prompt = prompts.render(
            "trainer-reference.mdc",
            username=username,
            background_color=background_color,
        )
        reference_refs: Sequence[pydantic_ai.UserContent] = [
            pydantic_ai.BinaryImage(data=likeness_bytes, media_type=likeness_media_type),
            pydantic_ai.BinaryImage(data=style_bible.load_trainer_style_bible_png(), media_type="image/png"),
            prompt.text,
        ]
        result = await self._image_agent_client().run(reference_refs)
        await _LOGGER.adebug(
            "Generated trainer reference",
            username=username,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            background_color=str(background_color),
        )
        return result.output.data, background_color

    async def detect_trainer_reference_facing(
        self,
        reference_png: bytes,
    ) -> sprite_types.SpriteFacing:
        facing = await sprite_facing.detect_sprite_facing(
            self._text_agent_client(),
            reference_png,
            subject="trainer character",
        )
        await _LOGGER.adebug("Detected trainer reference facing", facing=facing.value)
        return facing

    async def detect_vibemon_reference_facing(
        self,
        reference_png: bytes,
        *,
        vibemon_name: str,
    ) -> sprite_types.SpriteFacing:
        facing = await sprite_facing.detect_sprite_facing(
            self._text_agent_client(),
            reference_png,
            subject=f"Vibemon creature named {vibemon_name}",
        )
        await _LOGGER.adebug("Detected Vibemon reference facing", facing=facing.value, vibemon=vibemon_name)
        return facing

    async def generate_battle_cry_audio(self, vibemon: vibemon_entity.Vibemon) -> bytes:
        prompt = prompts.render("battle-cry.mdc", vibemon=vibemon)
        result = await self._text_agent_client().run(prompt.text, output_type=VibemonSound)
        await _LOGGER.adebug(
            "Generated Vibemon battle cry",
            vibemon=vibemon.name,
            prompt_name=prompt.name,
            prompt_version=prompt.version,
            **result.output.model_dump(),
        )
        stream = self._elevenlabs_client().text_to_sound_effects.convert(
            text=result.output.description,
            duration_seconds=result.output.duration,
        )
        return b"".join([audio_chunk async for audio_chunk in stream])


def validate_reference_likeness(data: bytes, *, media_type: str) -> None:
    """Reject reference uploads that are not decodable likeness images."""
    if media_type not in REFERENCE_LIKENESS_MEDIA:
        raise ValueError(f"Reference upload must be PNG, JPEG, or WebP; got {media_type!r}.")
    if not data:
        raise ValueError("Reference upload is empty.")
    if len(data) > _REFERENCE_MAX_BYTES:
        raise ValueError("Reference upload exceeds the 10 MB limit.")

    with Image.open(io.BytesIO(data)) as image:
        image.verify()


@ft.cache
def get_default_asset_generator() -> VibemonAssetGenerator:
    """Process-wide asset generator wired from ``Settings.load()``."""
    return VibemonAssetGenerator()


def _require_aesthetic(vibemon: vibemon_entity.Vibemon) -> None:
    if vibemon.aesthetic is None:
        raise ValueError("Vibemon aesthetic is required to generate sprite assets")


def _default_text_agent() -> Any:
    settings = Settings.load()
    return google.build_text_agent(settings.genai.text, settings.secrets)


def _default_image_agent() -> google.ImageAgent:
    settings = Settings.load()
    return google.build_image_agent(settings.genai.image, settings.secrets)


def _default_elevenlabs() -> AsyncElevenLabs:
    settings = Settings.load()
    return AsyncElevenLabs(api_key=settings.secrets.eleven_labs.get_secret_value())
