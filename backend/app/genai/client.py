from typing import TYPE_CHECKING
import re

from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.google import GoogleModel
import pydantic_ai
import structlog

from app.settings import settings
from app.genai import utils

if TYPE_CHECKING:
    from app import schema

_LOGGER = structlog.get_logger(__name__)

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
    p = utils.load_prompt("vibemon-name.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
    r = await FAST_TXT_AGENT.run(p)
    d = RX_WORDS_ONLY.sub(repl="", string=r.output)
    await _LOGGER.adebug("Generate :: Vibemon name", name=d, prompt=p)
    return d


async def generate_vibemon_sprite(vibemon: schema.Vibemon, bg_hex: str) -> bytes:
    """Generate a Vibemon's sprite sheet."""
    p = utils.load_prompt("sprite-sheet/__main__.mdc", vibemon=vibemon, bg_hex=bg_hex)
    r = await FAST_IMG_AGENT.run(p, builtin_tools=[pydantic_ai.ImageGenerationTool()], output_type=pydantic_ai.BinaryImage)
    await _LOGGER.adebug("Generate :: Vibemon sprite", vibemon=vibemon.name, prompt=p)
    d = r.output.data
    return d
