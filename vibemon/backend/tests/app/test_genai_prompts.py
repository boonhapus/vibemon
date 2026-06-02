from app.domains.vibemon.identity import BaseStats, Identity
from app.domains.vibemon.types import VibemonTypeT
from app.genai import prompts


def test_render_prompt_returns_metadata_and_text() -> None:
    rendered = prompts.render(
        "species-name.mdc",
        identity=Identity(name="__", elements=(VibemonTypeT.FIRE,), visual_notes="ember shell", base=BaseStats()),
        moves=[],
        visual_notes=None,
    )

    assert rendered.name == "vibemon-name"
    assert rendered.version == "1.1.1"
    assert rendered.path == "species-name.mdc"
    assert "Type: fire" in rendered.text
