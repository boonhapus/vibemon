import io

from PIL import Image, ImageDraw

from app.domains.vibemon.brand import CHROMA_KEY_CANDIDATES
from app.workflows import sprite_postprocess

_MATTE = CHROMA_KEY_CANDIDATES[2]  # Chroma Magenta


def test_normalize_trainer_reference_image_strips_solved_background() -> None:
    image = Image.new("RGB", (32, 32), str(_MATTE))
    ImageDraw.Draw(image).rectangle((8, 8, 24, 24), fill="#c0542a")

    rgba = Image.open(io.BytesIO(sprite_postprocess.normalize_trainer_reference_image(image, bg_color=_MATTE)))
    assert rgba.mode == "RGBA"
    corner: tuple[int, int, int, int] = rgba.getpixel((0, 0))  # type: ignore[assignment]
    center: tuple[int, int, int, int] = rgba.getpixel((16, 16))  # type: ignore[assignment]
    assert corner[3] == 0
    assert center[3] > 0


def test_normalize_trainer_reference_image_requires_bg_color() -> None:
    image = Image.new("RGB", (8, 8), "#ffffff")
    result = sprite_postprocess.normalize_trainer_reference_image(image, bg_color=_MATTE)
    assert isinstance(result, bytes)


def test_punch_enclosed_matte_holes_clears_trapped_chroma() -> None:
    matte = CHROMA_KEY_CANDIDATES[0]  # Chroma Green
    matte_rgb = matte.as_rgb()
    image = Image.new("RGB", (48, 48), matte_rgb)
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 8, 36, 40), fill="#c0542a")
    draw.rectangle((18, 14, 24, 30), fill=matte_rgb)

    rgba = Image.open(io.BytesIO(sprite_postprocess.normalize_trainer_reference_image(image, bg_color=matte)))
    hole: tuple[int, int, int, int] = rgba.getpixel((21, 20))  # type: ignore[assignment]
    assert hole[3] == 0


def test_normalize_trainer_reference_image_snaps_mismatched_matte() -> None:
    painted = (173, 106, 108)
    image = Image.new("RGB", (64, 64), painted)
    ImageDraw.Draw(image).rectangle((20, 12, 44, 52), fill="#8a5a40")

    rgba = Image.open(io.BytesIO(sprite_postprocess.normalize_trainer_reference_image(image, bg_color=_MATTE)))

    top_left: tuple[int, int, int, int] = rgba.getpixel((0, 0))  # type: ignore[assignment]
    center_pixel: tuple[int, int, int, int] = rgba.getpixel((32, 32))  # type: ignore[assignment]
    assert top_left[3] == 0
    assert center_pixel[3] > 0
