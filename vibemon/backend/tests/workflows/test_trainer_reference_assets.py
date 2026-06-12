import io

from PIL import Image, ImageDraw
import pytest

from app.domains.vibemon.brand import CHROMA_KEY_CANDIDATES
from app.workflows import asset_realization

_MATTE = CHROMA_KEY_CANDIDATES[2]  # Chroma Magenta


def test_normalize_trainer_reference_image_strips_solved_background() -> None:
    image = Image.new("RGB", (32, 32), str(_MATTE))
    ImageDraw.Draw(image).rectangle((8, 8, 24, 24), fill="#c0542a")

    rgba = Image.open(io.BytesIO(asset_realization.normalize_trainer_reference(image, bg_color=_MATTE)))
    assert rgba.mode == "RGBA"
    corner = rgba.getpixel((0, 0))
    center = rgba.getpixel((16, 16))
    assert corner[3] == 0
    assert center[3] > 0


def test_normalize_trainer_reference_image_requires_bg_color() -> None:
    image = Image.new("RGB", (8, 8), "#ffffff")
    with pytest.raises(TypeError):
        asset_realization.normalize_trainer_reference(image)


def test_punch_enclosed_matte_holes_clears_trapped_chroma() -> None:
    matte = CHROMA_KEY_CANDIDATES[0]  # Chroma Green
    matte_rgb = matte.as_rgb()
    image = Image.new("RGB", (48, 48), matte_rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 8, 36, 40), fill="#c0542a")
    draw.rectangle((18, 14, 24, 30), fill=matte_rgb)

    rgba = Image.open(io.BytesIO(asset_realization.normalize_trainer_reference(image, bg_color=matte)))
    hole = rgba.getpixel((21, 20))
    assert hole[3] == 0


def test_normalize_trainer_reference_image_snaps_mismatched_matte() -> None:
    painted = (173, 106, 108)
    image = Image.new("RGB", (64, 64), painted)
    ImageDraw.Draw(image).rectangle((20, 12, 44, 52), fill="#8a5a40")

    rgba = Image.open(io.BytesIO(asset_realization.normalize_trainer_reference(image, bg_color=_MATTE)))

    assert rgba.getpixel((0, 0))[3] == 0
    assert rgba.getpixel((32, 32))[3] > 0
