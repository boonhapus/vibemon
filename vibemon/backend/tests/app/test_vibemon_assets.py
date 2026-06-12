from typing import Any
import io

from PIL import Image
import pydantic_ai
import pytest

from app.domains.sprite import types as sprite_types
from app.domains.vibemon.entity import Aesthetic, Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import VibemonTypeT
from app.genai import google, sprite_facing, style_bible, vibemon_assets


class _RecordingImageAgent:
    supports_image_inputs = True

    def __init__(self) -> None:
        self.last_prompt: Any = None

    async def run(
        self,
        user_prompt: Any,
        *,
        output_type: Any = pydantic_ai.BinaryImage,
        builtin_tools: list[Any] | None = None,
    ) -> google.ImageRunResult:
        self.last_prompt = user_prompt
        image = Image.new("RGB", (16, 16), "#ffffff")
        payload = io.BytesIO()
        image.save(payload, format="PNG")
        return google.ImageRunResult(
            output=pydantic_ai.BinaryImage(data=payload.getvalue(), media_type="image/png"),
        )


class _RecordingTextAgent:
    def __init__(self, *, facing: sprite_types.SpriteFacing) -> None:
        self.facing = facing
        self.last_prompt: Any = None

    async def run(
        self,
        user_prompt: Any,
        *,
        output_type: Any = None,
        builtin_tools: list[Any] | None = None,
    ) -> Any:
        self.last_prompt = user_prompt
        return type(
            "TextRunResult",
            (),
            {"output": sprite_facing.SpriteFacingRead(facing=self.facing)},
        )()


@pytest.mark.asyncio
async def test_generate_trainer_reference_attaches_style_bible_and_likeness() -> None:
    agent = _RecordingImageAgent()
    generator = vibemon_assets.VibemonAssetGenerator(image_agent_factory=lambda: agent)

    likeness = io.BytesIO()
    Image.new("RGB", (12, 12), "#cccccc").save(likeness, format="PNG")
    likeness_bytes = likeness.getvalue()

    raw_reference, background_color = await generator.generate_trainer_reference(
        likeness_bytes,
        username="ada",
        likeness_media_type="image/png",
    )

    assert isinstance(raw_reference, bytes)
    assert str(background_color).startswith("#")

    assert isinstance(agent.last_prompt, list)
    assert len(agent.last_prompt) == 3
    assert agent.last_prompt[0].data == likeness_bytes
    assert agent.last_prompt[1].data == style_bible.load_trainer_style_bible_png()
    assert "LIKENESS LOCK" in agent.last_prompt[2]
    assert "Image 1: User likeness" in agent.last_prompt[2]


@pytest.mark.asyncio
async def test_detect_trainer_reference_facing_attaches_sprite_and_returns_label() -> None:
    agent = _RecordingTextAgent(facing=sprite_types.SpriteFacing.RIGHT)
    generator = vibemon_assets.VibemonAssetGenerator(text_agent_factory=lambda: agent)

    payload = io.BytesIO()
    Image.new("RGBA", (12, 12), (200, 80, 40, 255)).save(payload, format="PNG")
    reference_png = payload.getvalue()

    facing = await generator.detect_trainer_reference_facing(reference_png)

    assert facing is sprite_types.SpriteFacing.RIGHT
    assert isinstance(agent.last_prompt, list)
    assert len(agent.last_prompt) == 2
    assert agent.last_prompt[0].data == reference_png
    assert "trainer" in agent.last_prompt[1].lower()
    assert "sprite" in agent.last_prompt[1].lower()


@pytest.mark.asyncio
async def test_generate_reference_image_attaches_style_bible() -> None:
    agent = _RecordingImageAgent()
    generator = vibemon_assets.VibemonAssetGenerator(image_agent_factory=lambda: agent)

    vibemon = Vibemon(
        identity=Identity(
            name="Embertop",
            elements=(VibemonTypeT.FIRE,),
            visual_notes="ember shell",
            base=BaseStats(),
        ),
    )
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)

    await generator.generate_reference_image(vibemon)

    assert isinstance(agent.last_prompt, list)
    assert len(agent.last_prompt) == 3
    assert agent.last_prompt[0].data == style_bible.load_trainer_style_bible_png()
    assert agent.last_prompt[1].data == style_bible.load_hatchling_style_bible_png()
    assert "COZY HANDHELD SPRITE STYLE" in agent.last_prompt[2]
