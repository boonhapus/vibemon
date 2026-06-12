"""Detect sprite orientation and derive mirrored left/right pose pairs."""

from typing import Any, Final, Literal
import io

from PIL import Image
import pydantic
import pydantic_ai

from app.domains.sprite import types as sprite_types
from app.genai import prompts

GearPoseLabel = Literal["left", "right"]

GEAR_CENTER_DEFAULT_FACING: Final[dict[str, sprite_types.SpriteFacing]] = {
    "camera": sprite_types.SpriteFacing.LEFT,
    "vibe-deck": sprite_types.SpriteFacing.RIGHT,
    "vibe-cart": sprite_types.SpriteFacing.RIGHT,
}

GEAR_FACING_SUBJECTS: Final[dict[str, str]] = {
    "camera": "vintage instant camera object",
    "vibe-deck": "closed clamshell Vibe Deck field device",
    "vibe-cart": "Vibe Cart capture cartridge",
}


class SpriteFacingRead(pydantic.BaseModel):
    """Vision-model read of horizontal orientation in a sprite image."""

    facing: sprite_types.SpriteFacing


async def detect_sprite_facing(
    text_agent: Any,
    sprite_png: bytes,
    *,
    subject: str,
) -> sprite_types.SpriteFacing:
    if not sprite_png:
        raise ValueError("sprite PNG is empty")

    with Image.open(io.BytesIO(sprite_png)) as image:
        image.verify()

    prompt = prompts.render("sprite-facing.mdc", subject=subject)
    result = await text_agent.run(
        [
            pydantic_ai.BinaryImage(data=sprite_png, media_type="image/png"),
            prompt.text,
        ],
        output_type=SpriteFacingRead,
    )
    return result.output.facing


def resolve_gear_source_facing(
    detected: sprite_types.SpriteFacing,
    gear_key: str,
) -> sprite_types.SpriteFacing:
    """Map vision output plus gear defaults to the pose label for the source file."""
    if detected is sprite_types.SpriteFacing.CENTER:
        return GEAR_CENTER_DEFAULT_FACING.get(gear_key, sprite_types.SpriteFacing.RIGHT)
    return detected


def gear_pose_label(facing: sprite_types.SpriteFacing) -> GearPoseLabel:
    if facing is sprite_types.SpriteFacing.LEFT:
        return "left"
    return "right"


async def derive_gear_poses(
    gear_key: str,
    source_rgba: bytes,
    text_agent: Any,
) -> tuple[
    dict[GearPoseLabel, bytes],
    sprite_types.SpriteFacing,
    sprite_types.SpriteFacing,
    GearPoseLabel,
]:
    """Classify source orientation and return mirrored left/right pose PNGs."""
    if gear_key not in GEAR_FACING_SUBJECTS:
        raise ValueError(f"Unknown gear key {gear_key!r}")

    detected = await detect_sprite_facing(
        text_agent,
        source_rgba,
        subject=GEAR_FACING_SUBJECTS[gear_key],
    )
    source_facing = resolve_gear_source_facing(detected, gear_key)
    poses = derive_left_right_poses(source_rgba, source_facing)
    return poses, detected, source_facing, gear_pose_label(source_facing)


def derive_left_right_poses(
    source_rgba: bytes,
    source_facing: sprite_types.SpriteFacing,
) -> dict[GearPoseLabel, bytes]:
    """Return left and right pose PNGs from one source and its detected facing."""
    from app.genai import static_assets

    if source_facing is sprite_types.SpriteFacing.LEFT:
        return {
            "left": source_rgba,
            "right": static_assets.mirror_png_rgba(source_rgba),
        }
    return {
        "right": source_rgba,
        "left": static_assets.mirror_png_rgba(source_rgba),
    }
