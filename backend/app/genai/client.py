from typing import TYPE_CHECKING
import re

from elevenlabs import AsyncElevenLabs
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.google import GoogleModel
import pydantic_ai
import structlog

from app.settings import settings
from app.genai import structured_output, utils

if TYPE_CHECKING:
    from app import schema

_LOGGER = structlog.get_logger(__name__)

_eleven_labs = AsyncElevenLabs(api_key=settings.eleven_labs_api_key.get_secret_value())
_ai_provider = GoogleProvider(api_key=settings.google_api_key.get_secret_value())
_texts_model = GoogleModel(settings.txt_ai_model, provider=_ai_provider)
_image_model = GoogleModel(settings.img_ai_model, provider=_ai_provider)

FAST_TXT_AGENT = pydantic_ai.Agent(_texts_model)
FAST_IMG_AGENT = pydantic_ai.Agent(_image_model)


# ── CLEANERS ──────────────────────────────────────────────────────────────────────────

RX_WORDS_ONLY = re.compile(r"[^\w-]")


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────

async def generate_vibemon_name(identity: schema.Identity, moves: list[schema.Move], visual_notes: str | None) -> str:
    """Generate a Vibemon's name."""
    p = utils.load_prompt("species-name.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
    r = await FAST_TXT_AGENT.run(p)
    d = RX_WORDS_ONLY.sub(repl="", string=r.output)
    await _LOGGER.adebug("Generate :: Vibemon name", name=d, prompt=p)
    return d


async def generate_vibemon_sprite(vibemon: schema.Vibemon, bg_hex: str) -> bytes:
    """Generate a Vibemon's sprite sheet."""
    p = utils.load_prompt("sprite-sheet.mdc", vibemon=vibemon, bg_hex=bg_hex)
    r = await FAST_IMG_AGENT.run(p, builtin_tools=[pydantic_ai.ImageGenerationTool()], output_type=pydantic_ai.BinaryImage)
    await _LOGGER.adebug("Generate :: Vibemon sprite", vibemon=vibemon.name, prompt=p)
    d = r.output.data
    return d


async def generate_battle_cry(vibemon: schema.Vibemon) -> bytes:
    """Generate a Vibemon battle cry."""
    p = utils.load_prompt("battle-cry.mdc", vibemon=vibemon)
    r = await FAST_TXT_AGENT.run(p, output_type=structured_output.VibemonSound)
    await _LOGGER.adebug("Generate :: Vibemon battle cry", vibemon=vibemon.name, **r.output.model_dump())

    r = _eleven_labs.text_to_sound_effects.convert(text=r.output.description, duration_seconds=r.output.duration)
    d = b"".join([audio_chunk async for audio_chunk in r])
    return d
