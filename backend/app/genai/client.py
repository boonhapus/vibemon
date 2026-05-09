from typing import TYPE_CHECKING
import re

from elevenlabs import AsyncElevenLabs
import pydantic_ai
import structlog

from app.settings import settings
from app import utils as app_utils
from app.genai import _image, structured_output, utils

if TYPE_CHECKING:
    from app import schema

_LOGGER = structlog.get_logger(__name__)

_eleven_labs = AsyncElevenLabs(api_key=settings.eleven_labs_api_key.get_secret_value())

FAST_TXT_AGENT = pydantic_ai.Agent(settings.txt_ai_model)
FAST_IMG_AGENT = _image.build_image_agent(settings.img_ai_model)

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


async def generate_vibemon_sprite(vibemon: schema.Vibemon) -> bytes:
    """Generate a Vibemon's sprite sheet."""
    p = utils.load_prompt("sprite-reference.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run(p)
    await _LOGGER.adebug("Generate :: Vibemon sprite reference", vibemon=vibemon.name, prompt=p)

    # TODO: this should likely be returned to the frontend, and then the sprite-sheet
    #       generated once this mon is adopted. that way we save on the second image
    #       generation cost if the user doesn't like this one. the second generation is
    #       primarily to support UI function anyway.
    d = app_utils.normalize_sprite_matte(
        r.output.data,
        bg_color=vibemon.aesthetic.background_color,
        rows=1,
        cols=1,
    )

    p = utils.load_prompt("sprite-sheet.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run([pydantic_ai.BinaryImage(data=d, media_type="image/png"), p])
    d = app_utils.normalize_sprite_matte(r.output.data, bg_color=vibemon.aesthetic.background_color)

    if issues := app_utils.validate_sprite_sheet(d):
        raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")

    return d


async def generate_battle_cry(vibemon: schema.Vibemon) -> bytes:
    """Generate a Vibemon battle cry."""
    p = utils.load_prompt("battle-cry.mdc", vibemon=vibemon)
    r = await FAST_TXT_AGENT.run(p, output_type=structured_output.VibemonSound)
    await _LOGGER.adebug("Generate :: Vibemon battle cry", vibemon=vibemon.name, **r.output.model_dump())

    r = _eleven_labs.text_to_sound_effects.convert(text=r.output.description, duration_seconds=r.output.duration)
    d = b"".join([audio_chunk async for audio_chunk in r])
    return d
