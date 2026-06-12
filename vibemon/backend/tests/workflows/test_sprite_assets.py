import io

from PIL import Image, ImageDraw
import numpy as np
import pytest

from app.domains.vibemon.brand import CHROMA_KEY_CANDIDATES, Color
from app.workflows import rmbg, sprite_postprocess

_MATTE = CHROMA_KEY_CANDIDATES[2]  # Chroma Magenta


def test_key_sprite_preserves_existing_alpha() -> None:
    matte = (0, 71, 171)
    crop = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(crop)
    draw.ellipse((30, 30, 70, 70), fill=(100, 180, 50, 255))

    rgba = rmbg.key_sprite(crop, bg_color=matte)
    arr = np.asarray(rgba)

    assert arr[0, 0, 3] < 32
    assert arr[50, 50, 3] > 200


def test_resolve_background_color_prefers_detected_matte() -> None:
    requested = (0, 71, 171)
    actual = (87, 119, 150)
    image = Image.new("RGB", (120, 120), actual)
    draw = ImageDraw.Draw(image)
    draw.ellipse((40, 40, 80, 80), fill=(40, 180, 60))

    resolved = rmbg.resolve_background_color(image, requested)

    assert resolved == actual


def test_extracted_pose_encodes_with_alpha() -> None:
    matte = _MATTE
    sheet = Image.new("RGB", (300, 300), str(matte))
    draw = ImageDraw.Draw(sheet)
    for row in range(3):
        for col in range(3):
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill="#228822")
    normalized_sheet = sprite_postprocess.normalize_sprite_matte(sheet, bg_color=matte)
    crop = next(iter(sprite_postprocess.extract_sprites(normalized_sheet, bg_color=matte).values()))

    alpha = np.asarray(Image.open(io.BytesIO(sprite_postprocess.encode_rgba_png(crop))))[..., 3]

    assert (alpha < 32).sum() > 0
    assert (alpha >= 128).sum() > 0


def test_reprocess_reference_flattens_existing_alpha_before_rekey() -> None:
    matte = (0, 177, 64)  # Chroma Green
    source = Image.new("RGB", (80, 80), matte)
    draw = ImageDraw.Draw(source)
    draw.ellipse((20, 20, 60, 60), fill=(60, 120, 70))
    first_pass = rmbg.key_sprite(
        source,
        bg_color=matte,
        step_tolerance=30,
    )

    from app.domains.vibemon.entity import Aesthetic, Vibemon
    from app.domains.vibemon.identity import BaseStats, Identity
    from app.domains.vibemon.types import VibemonTypeT

    vibemon = Vibemon(
        identity=Identity(
            name="Mossling",
            elements=(VibemonTypeT.GRASS,),
            visual_notes="",
            provider_visual_notes="",
            base=BaseStats(),
        ),
        aesthetic=Aesthetic(
            primary_color=_MATTE,
            background_color=Color("#00B140", "Chroma Green", "test matte"),
        ),
    )
    reprocessed = Image.open(
        io.BytesIO(
            sprite_postprocess.normalize_reference_image(
                first_pass,
                bg_color=vibemon.aesthetic.background_color,
            )
        )
    )
    alpha = np.asarray(reprocessed)[..., 3]

    assert (alpha >= 128).sum() >= (np.asarray(first_pass)[..., 3] >= 128).sum()


def test_connected_flood_preserves_interior_dither_on_green_matte() -> None:
    matte = (0, 177, 64)
    source = Image.new("RGB", (64, 64), matte)
    draw = ImageDraw.Draw(source)
    draw.rectangle((16, 16, 48, 48), fill=(55, 130, 75))
    for x in range(18, 46, 2):
        for y in range(18, 46, 2):
            source.putpixel((x, y), (40, 150, 60))

    rgba = rmbg.key_sprite(
        source,
        bg_color=matte,
        despill=False,
    )
    interior = np.s_[20:44, 20:44]
    holes = int((np.asarray(rgba)[interior][..., 3] < 32).sum())

    assert holes == 0


def test_reference_key_preserves_dithered_interior_on_green_matte() -> None:
    matte = (0, 177, 64)
    source = Image.new("RGB", (64, 64), matte)
    draw = ImageDraw.Draw(source)
    draw.rectangle((16, 16, 48, 48), fill=(55, 130, 75))
    for x in range(18, 46, 2):
        for y in range(18, 46, 2):
            source.putpixel((x, y), (40, 150, 60))

    from app.domains.vibemon.entity import Aesthetic, Vibemon
    from app.domains.vibemon.identity import BaseStats, Identity
    from app.domains.vibemon.types import VibemonTypeT

    vibemon = Vibemon(
        identity=Identity(
            name="Ditherling",
            elements=(VibemonTypeT.GRASS,),
            visual_notes="",
            provider_visual_notes="",
            base=BaseStats(),
        ),
        aesthetic=Aesthetic(
            primary_color=Color("#228822", "Grass", "test fill"),
            background_color=Color("#00B140", "Chroma Green", "test matte"),
        ),
    )
    normalized = Image.open(
        io.BytesIO(
            sprite_postprocess.normalize_reference_image(
                source,
                bg_color=vibemon.aesthetic.background_color,
            )
        )
    )
    interior = np.s_[20:44, 20:44]
    holes = int((np.asarray(normalized)[interior][..., 3] < 32).sum())

    assert holes == 0


def test_key_sprite_uses_known_matte() -> None:
    matte = (255, 0, 255)
    image = Image.new("RGB", (40, 40), matte)
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 10, 28, 30), fill=(40, 180, 60))

    rgba = rmbg.key_sprite(image, bg_color=matte)
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

    out = sprite_postprocess.normalize_sprite_matte(image, bg_color=matte)
    normalized = Image.open(io.BytesIO(out)).convert("RGB")

    assert normalized.getpixel((0, 0)) == matte.as_rgb()
    assert normalized.getpixel((24, 24)) != matte.as_rgb()


def test_extract_grid_cells_supports_non_square_grids() -> None:
    matte = _MATTE
    image = Image.new("RGB", (400, 600), str(matte))
    draw = ImageDraw.Draw(image)
    rows, cols = 6, 4
    for row in range(rows):
        for col in range(cols):
            cx = int((col + 0.5) * 400 / cols)
            cy = int((row + 0.5) * 600 / rows)
            draw.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill="#228822")

    sheet = sprite_postprocess.normalize_sprite_matte(image, bg_color=matte)
    cells = sprite_postprocess.extract_grid_cells(sheet, bg_color=matte, rows=rows, cols=cols)

    assert len(cells) == 24
    assert all(cell.mode == "RGBA" and max(cell.size) > 1 for cell in cells)


def test_validate_and_extract_sprite_sheet() -> None:
    matte = _MATTE
    image = Image.new("RGB", (300, 300), str(matte))
    draw = ImageDraw.Draw(image)
    for row in range(3):
        for col in range(3):
            cx = col * 100 + 50
            cy = row * 100 + 50
            draw.ellipse((cx - 20, cy - 24, cx + 20, cy + 24), fill="#228822")

    sheet = sprite_postprocess.normalize_sprite_matte(image, bg_color=matte)
    assert sprite_postprocess.validate_sprite_sheet(sheet, bg_color=matte) == []

    poses = sprite_postprocess.extract_sprites(sheet, bg_color=matte)
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

    sheet = sprite_postprocess.normalize_sprite_matte(image, bg_color=matte)
    issues = sprite_postprocess.validate_sprite_sheet(sheet, bg_color=matte)

    assert any("R1C1" in issue for issue in issues)


def test_extract_sprites_requires_foreground() -> None:
    matte = _MATTE
    flat = sprite_postprocess.normalize_sprite_matte(Image.new("RGB", (90, 90), str(matte)), bg_color=matte)

    with pytest.raises(RuntimeError, match="No foreground detected"):
        sprite_postprocess.extract_sprites(flat, bg_color=matte, rows=1, cols=1)
