from typing import TYPE_CHECKING, Any
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
SPRITE_SHEET_MAX_ATTEMPTS = 3

# ── CLEANERS ──────────────────────────────────────────────────────────────────────────

RX_WORDS_ONLY = re.compile(r"[^\w-]")


# ── IDENTITY ──────────────────────────────────────────────────────────────────────────
def _save_data(data: Any, vibemon: str, filename: str) -> None:
    import pathlib

    here = pathlib.Path(__file__).parent
    root = here.parent.parent.parent
    path = root.joinpath(f".scripts/generated/{vibemon}/input")
    path.mkdir(parents=True, exist_ok=True)

    if isinstance(data, bytes):
        path.joinpath(filename).write_bytes(data)
    else:
        path.joinpath(filename).write_text(data, encoding="utf-8")


def _sprite_sheet_retry_prompt(prompt: str, issues: list[str]) -> str:
    issue_text = "; ".join(issues)

    return (
        f"{prompt}\n\n"
        "RETRY CORRECTION\n"
        f"The previous sheet failed automated validation: {issue_text}.\n"
        "Regenerate the entire sprite contact sheet from scratch. Keep the same attached reference creature. "
        "The new output must contain exactly one complete main creature body centered in each of the nine cells, "
        "with no blank cells, no merged poses, and no floating symbols or extra marks."
    )


async def generate_vibemon_name(identity: schema.Identity, moves: list[schema.Move], visual_notes: str | None) -> str:
    """Generate a Vibemon's name."""
    n = "species-name"
    p = utils.load_prompt(f"{n}.mdc", identity=identity, moves=moves, visual_notes=visual_notes)
    r = await FAST_TXT_AGENT.run(p)
    d = RX_WORDS_ONLY.sub(repl="", string=r.output)
    await _LOGGER.adebug("Generate :: Vibemon name", name=d, prompt=p)
    _save_data(p, vibemon=d, filename=f"{n}_prompt.txt")
    return d


async def generate_vibemon_sprite(vibemon: schema.Vibemon) -> bytes:
    """Generate a Vibemon's sprite sheet."""
    n = "sprite-reference"
    p = utils.load_prompt(f"{n}.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run(p)
    await _LOGGER.adebug("Generate :: Vibemon sprite reference", vibemon=vibemon.name, prompt=p)

    # TODO: this should likely be returned to the frontend, and then the sprite-sheet
    #       generated once this mon is adopted. that way we save on the second image
    #       generation cost if the user doesn't like this one. the second generation is
    #       primarily to support UI function anyway.
    d = app_utils.normalize_sprite_matte(
        r.output.data,
        background_color=vibemon.aesthetic.background_color,
        rows=1,
        cols=1,
    )
    _save_data(p, vibemon=vibemon.name, filename=f"{n}_prompt.txt")
    _save_data(d, vibemon=vibemon.name, filename=f"{n}_output.png")

    n = "sprite-sheet"
    base_prompt = utils.load_prompt(f"{n}.mdc", vibemon=vibemon)
    p = base_prompt
    issues: list[str] = []

    for attempt in range(1, SPRITE_SHEET_MAX_ATTEMPTS + 1):
        r = await FAST_IMG_AGENT.run([pydantic_ai.BinaryImage(data=d, media_type="image/png"), p])
        normalized = app_utils.normalize_sprite_matte(
            r.output.data,
            background_color=vibemon.aesthetic.background_color,
        )
        issues = app_utils.validate_sprite_sheet(normalized)

        if not issues:
            d = normalized
            await _LOGGER.adebug(
                "Generate :: Vibemon sprite",
                vibemon=vibemon.name,
                prompt=p,
                attempt=attempt,
            )
            break

        await _LOGGER.awarning(
            "Generate :: Vibemon sprite sheet failed validation",
            vibemon=vibemon.name,
            attempt=attempt,
            issues=issues,
        )
        p = _sprite_sheet_retry_prompt(base_prompt, issues)
    else:
        raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")

    _save_data(p, vibemon=vibemon.name, filename=f"{n}_prompt.txt")
    _save_data(d, vibemon=vibemon.name, filename=f"{n}_output.png")
    return d


async def generate_battle_cry(vibemon: schema.Vibemon) -> bytes:
    """Generate a Vibemon battle cry."""
    n = "battle-cry"
    p = utils.load_prompt(f"{n}.mdc", vibemon=vibemon)
    r = await FAST_TXT_AGENT.run(p, output_type=structured_output.VibemonSound)
    await _LOGGER.adebug("Generate :: Vibemon battle cry", vibemon=vibemon.name, **r.output.model_dump())

    r = _eleven_labs.text_to_sound_effects.convert(text=r.output.description, duration_seconds=r.output.duration)
    d = b"".join([audio_chunk async for audio_chunk in r])
    _save_data(p, vibemon=vibemon.name, filename=f"{n}_prompt.txt")
    return d
