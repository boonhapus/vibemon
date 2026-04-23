from collections.abc import Iterable
import re

from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.models.google import GoogleModel
import pydantic_ai

from app.settings import settings
from app.genai import utils
from app import types

_ai_provider = GoogleProvider(api_key=settings.google_api_key.get_secret_value())
_texts_model = GoogleModel(settings.texts_ai_model, provider=_ai_provider)
_image_model = GoogleModel(settings.image_ai_model, provider=_ai_provider)

FAST_AGENT = pydantic_ai.Agent(_texts_model)

# ── CLEANERS ──────────────────────────────────────────────────────────────────────────

RX_WORDS_ONLY = re.compile(r"[^\w-]")


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────

async def generate_vibemon_name(elements: Iterable[types.VibemonTypeT]) -> str:
    """Generate a Vibemon's name."""
    p = utils.load_prompt("vibemon-name", elements=" AND ".join(f"'{e}'" for e in elements))
    r = await FAST_AGENT.run(p)
    d = RX_WORDS_ONLY.sub(repl="", string=r.output)
    return d
