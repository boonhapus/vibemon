import io

from PIL import Image
import pytest

from app.domains.vibemon.entity import Aesthetic, Vibemon
from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import VibemonTypeT
from app.genai import prompts, vibemon_assets


def _prompt_vibemon() -> Vibemon:
    vibemon = Vibemon(
        identity=Identity(
            name="Embertop",
            elements=(VibemonTypeT.FIRE,),
            visual_notes="clear heat",
            base=BaseStats(),
        ),
    )
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)
    return vibemon


def test_render_prompt_returns_metadata_and_text() -> None:
    rendered = prompts.render(
        "species-name.mdc",
        identity=Identity(name="__", elements=(VibemonTypeT.FIRE,), visual_notes="ember shell", base=BaseStats()),
        moves=[],
    )

    assert rendered.name == "vibemon-name"
    assert rendered.version == "1.2.0"
    assert rendered.path == "species-name.mdc"
    assert "Type: fire" in rendered.text


def test_sprite_reference_prompt_uses_goldilocks_style_without_pokemon_language() -> None:
    rendered = prompts.render("sprite-reference.mdc", vibemon=_prompt_vibemon())

    assert rendered.version == "1.5.0"
    lowered = rendered.text.lower()
    assert "cozy handheld sprite style" in lowered
    assert "style bible" in lowered
    assert "creature fills only" in lowered
    assert "isolation" in lowered
    assert "no drop shadow baked into the sprite" in lowered
    assert "body shading only" in lowered
    # Chroma-key direction must carry hex + name + saturation intent so the model
    # paints the true key instead of a muted slate the matte solver can't separate.
    matte = _prompt_vibemon().aesthetic.background_color
    assert matte.hex in rendered.text
    assert matte.name in rendered.text
    assert "chroma-key" in lowered
    assert "fully saturated" in lowered
    assert "never appear anywhere on the creature" in lowered
    assert "pokémon-style" not in lowered
    assert "pokemon-style" not in lowered
    assert "pokémon sugimori" not in lowered


def test_sprite_sheet_prompt_uses_reference_style_lock_without_sugimori() -> None:
    rendered = prompts.render("sprite-sheet.mdc", vibemon=_prompt_vibemon())

    assert rendered.version == "1.8.0"
    lowered = rendered.text.lower()
    assert "match the attached reference image's rendering style" in lowered
    assert "do not copy it" in lowered
    assert "no drop shadow baked into any sprite" in lowered
    assert "pokémon sugimori style" not in lowered
    assert "pokémon-style" not in lowered


def test_sprite_facing_prompt_requests_structured_label() -> None:
    rendered = prompts.render("sprite-facing.mdc", subject="vintage camera object")

    assert rendered.version == "1.0.0"
    lowered = rendered.text.lower()
    assert "left" in lowered
    assert "center" in lowered
    assert "right" in lowered
    assert "vintage camera object" in lowered
    assert "facing`: one of" in lowered

    trainer_rendered = prompts.render("sprite-facing.mdc", subject="trainer character")
    assert "trainer character" in trainer_rendered.text.lower()


def test_trainer_reference_prompt_includes_likeness_and_trainer_archetype() -> None:
    rendered = prompts.render(
        "trainer-reference.mdc",
        username="ada",
        background_color="#00B140",
    )

    assert rendered.version == "1.8.0"
    lowered = rendered.text.lower()
    assert "reference images" in lowered
    assert "image 1: user likeness" in lowered
    assert "image 2: style-bible trainer" in lowered
    assert "priority" in lowered
    assert "image 1 likeness always wins" in lowered
    assert "trainer archetype always wins" in lowered
    assert "group photos" in lowered
    assert "distinctive facial features" in lowered
    assert "ethnicity lock" in lowered
    assert "generic game protagonist" in lowered
    assert "if image 1 shows a white subject" in lowered
    assert "formal-wear override" in lowered
    assert "suit + tie" in lowered
    assert "likeness lock" in lowered
    assert "trainer archetype" in lowered
    assert "identity (hard lock)" in lowered
    assert "rendering fidelity" in lowered
    assert "cropped or face-heavy" in lowered
    assert "adult-leaning silhouette" in lowered
    assert "not a chibi or child body" in lowered
    assert "palette hint" in lowered
    assert "default trainer kit" in lowered
    assert "skirt stays a skirt" in lowered
    assert "never render photo-real street clothes" in lowered
    assert "never a flat single-tone face or washed-out skin" in lowered
    assert "technical chroma key" in lowered
    assert "cozy handheld trainer rendering" in lowered
    assert "background pixels must be exactly" in lowered
    assert "48-64px-tall battle sprite" not in lowered
    assert "320x180" not in lowered
    assert "cozy handheld sprite style" not in lowered
    assert "#00b140" in lowered
    assert "comfortable pants" not in lowered
    assert "gear lock" not in lowered
    assert "never large backpacks" not in lowered
    assert "#ffffff" not in lowered


def test_validate_reference_likeness_rejects_empty_payload() -> None:
    with pytest.raises(ValueError, match="empty"):
        vibemon_assets.validate_reference_likeness(b"", media_type="image/png")


def test_validate_reference_likeness_accepts_png_bytes() -> None:
    payload = io.BytesIO()
    Image.new("RGB", (8, 8), "#ffffff").save(payload, format="PNG")
    vibemon_assets.validate_reference_likeness(payload.getvalue(), media_type="image/png")
