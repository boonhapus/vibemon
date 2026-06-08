import io

from PIL import Image, ImageDraw
import numpy as np
import pytest

from app.domains.vibemon.brand import CHROMA_KEY_CANDIDATES
from app.workflows import _sprite_assets as sprite_assets

_MATTE = CHROMA_KEY_CANDIDATES[2]  # Chroma Magenta


def test_remove_solid_background_preserves_existing_alpha() -> None:
    matte = (0, 71, 171)
    crop = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(crop)
    draw.ellipse((30, 30, 70, 70), fill=(100, 180, 50, 255))

    rgba = sprite_assets.remove_solid_background(crop, bg_color=matte)
    arr = np.asarray(rgba)

    assert arr[0, 0, 3] < 32
    assert arr[50, 50, 3] > 200


def test_resolve_background_color_prefers_detected_matte() -> None:
    requested = (0, 71, 171)
    actual = (87, 119, 150)
    image = Image.new("RGB", (120, 120), actual)
    draw = ImageDraw.Draw(image)
    draw.ellipse((40, 40, 80, 80), fill=(40, 180, 60))

    resolved = sprite_assets.resolve_background_color(image, requested)

    assert resolved == actual


def test_normalize_pose_image_keeps_transparent_crop() -> None:
    from app.domains.vibemon.entity import Aesthetic, Vibemon
    from app.domains.vibemon.identity import BaseStats, Identity
    from app.domains.vibemon.types import VibemonTypeT

    matte = _MATTE
    sheet = Image.new("RGB", (300, 300), str(matte))
    draw = ImageDraw.Draw(sheet)
    for row in range(3):
        for col in range(3):
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill="#228822")
    normalized_sheet = sprite_assets.normalize_sprite_matte(sheet, bg_color=matte)
    poses = sprite_assets.extract_sprites(normalized_sheet, bg_color=matte)
    crop = next(iter(poses.values()))

    vibemon = Vibemon(
        identity=Identity(
            name="Testling",
            elements=(VibemonTypeT.GRASS,),
            visual_notes="",
            provider_visual_notes="",
            base=BaseStats(),
        ),
        aesthetic=Aesthetic(
            primary_color=_MATTE,
            background_color=matte,
        ),
    )
    pose_bytes = sprite_assets.normalize_pose_image(crop, vibemon)
    alpha = np.asarray(Image.open(io.BytesIO(pose_bytes)))[..., 3]

    assert (alpha < 32).sum() > 0
    assert (alpha >= 128).sum() > 0


def test_remove_solid_background_uses_known_matte() -> None:
    matte = (255, 0, 255)
    image = Image.new("RGB", (40, 40), matte)
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 10, 28, 30), fill=(40, 180, 60))

    rgba = sprite_assets.remove_solid_background(image, bg_color=matte)
    arr = np.asarray(rgba)

    assert arr[0, 0, 3] < 32
    assert arr[20, 20, 3] > 200


def test_normalize_sprite_matte_snaps_background() -> None:
    matte = _MATTE
    image = Image.new("RGB", (48, 48), str(matte))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 30, 30), fill="#228822")
    # Slight matte drift in a corner (simulates model noise)
    image.putpixel((0, 0), (210, 25, 140))

    out = sprite_assets.normalize_sprite_matte(image, bg_color=matte)
    normalized = Image.open(io.BytesIO(out)).convert("RGB")

    assert normalized.getpixel((0, 0)) == sprite_assets._hex_rgb(matte)
    assert normalized.getpixel((24, 24)) != sprite_assets._hex_rgb(matte)


def test_validate_and_extract_sprite_sheet() -> None:
    matte = _MATTE
    image = Image.new("RGB", (300, 300), str(matte))
    draw = ImageDraw.Draw(image)
    for row in range(3):
        for col in range(3):
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill="#228822")

    sheet = sprite_assets.normalize_sprite_matte(image, bg_color=matte)
    assert sprite_assets.validate_sprite_sheet(sheet, bg_color=matte) == []

    poses = sprite_assets.extract_sprites(sheet, bg_color=matte)
    assert len(poses) == 9
    assert all(img.mode == "RGBA" and max(img.size) > 1 for img in poses.values())


def test_validate_sprite_sheet_flags_empty_cell() -> None:
    matte = _MATTE
    image = Image.new("RGB", (300, 300), str(matte))
    draw = ImageDraw.Draw(image)
    for row in range(3):
        for col in range(3):
            if row == 0 and col == 0:
                continue
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill="#228822")

    sheet = sprite_assets.normalize_sprite_matte(image, bg_color=matte)
    issues = sprite_assets.validate_sprite_sheet(sheet, bg_color=matte)

    assert any("R1C1" in issue for issue in issues)


def test_extract_sprites_requires_foreground() -> None:
    matte = _MATTE
    flat = sprite_assets.normalize_sprite_matte(Image.new("RGB", (90, 90), str(matte)), bg_color=matte)

    with pytest.raises(RuntimeError, match="No foreground detected"):
        sprite_assets.extract_sprites(flat, bg_color=matte, rows=1, cols=1)
