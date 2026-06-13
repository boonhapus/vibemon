import pathlib

import pytest

from app.domains.vibemon import brand
from app.genai import static_assets


def _write_prompt(path: pathlib.Path, frontmatter: str, body: str = "Draw the thing.") -> None:
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")


def test_parse_asset_prompt_reads_reference_metadata(tmp_path: pathlib.Path) -> None:
    prompt_path = tmp_path / "icons" / "deck.mdc"
    prompt_path.parent.mkdir(parents=True)
    _write_prompt(
        prompt_path,
        "\n".join(
            [
                "name: deck-icon",
                "asset: static/game/icons/deck.png",
                "model: gemini-3-pro-image",
                "reference_asset: static/game/sprites/deck.png",
                "depends_on: deck-sprite",
            ]
        ),
    )

    record = static_assets.parse_asset_prompt(prompt_path)

    assert record.name == "deck-icon"
    assert record.reference_asset == "static/game/sprites/deck.png"
    assert record.depends_on == "deck-sprite"


def test_expand_with_dependencies_orders_sprite_before_icon(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "deck.mdc"
    icon_path = tmp_path / "icons" / "deck.mdc"
    sprite_path.parent.mkdir(parents=True)
    icon_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: deck-sprite",
                "asset: static/game/sprites/deck.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )
    _write_prompt(
        icon_path,
        "\n".join(
            [
                "name: deck-icon",
                "asset: static/game/icons/deck.png",
                "model: gemini-3-pro-image",
                "reference_asset: static/game/sprites/deck.png",
                "depends_on: deck-sprite",
            ]
        ),
    )

    all_records = [
        static_assets.parse_asset_prompt(sprite_path),
        static_assets.parse_asset_prompt(icon_path),
    ]
    expanded = static_assets.expand_with_dependencies(
        [all_records[1]],
        all_records=all_records,
    )

    assert [record.name for record in expanded] == ["deck-sprite", "deck-icon"]


def test_sort_for_generation_puts_reference_icons_last(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "deck.mdc"
    icon_path = tmp_path / "icons" / "deck.mdc"
    settings_path = tmp_path / "icons" / "settings.mdc"
    sprite_path.parent.mkdir(parents=True)
    icon_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: deck-sprite",
                "asset: static/game/sprites/deck.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )
    _write_prompt(
        icon_path,
        "\n".join(
            [
                "name: deck-icon",
                "asset: static/game/icons/deck.png",
                "model: gemini-3-pro-image",
                "reference_asset: static/game/sprites/deck.png",
            ]
        ),
    )
    _write_prompt(
        settings_path,
        "\n".join(
            [
                "name: settings-icon",
                "asset: static/game/icons/settings.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )

    records = static_assets.sort_for_generation(
        [
            static_assets.parse_asset_prompt(sprite_path),
            static_assets.parse_asset_prompt(icon_path),
            static_assets.parse_asset_prompt(settings_path),
        ]
    )

    assert [record.name for record in records] == ["deck-sprite", "settings-icon", "deck-icon"]


def test_resolve_reference_bytes_prefers_generated_cache(tmp_path: pathlib.Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    cached = {b"cached-bytes"}
    resolved = static_assets.resolve_reference_bytes(
        "static/game/sprites/deck.png",
        output_dir=output_dir,
        generated_cache={"game/sprites/deck.png": cached},
    )

    assert resolved == cached


def test_resolve_reference_bytes_reads_output_dir(tmp_path: pathlib.Path) -> None:
    output_dir = tmp_path / "out"
    asset_path = output_dir / "game" / "sprites" / "deck.png"
    asset_path.parent.mkdir(parents=True)
    asset_path.write_bytes(b"fresh-bytes")

    resolved = static_assets.resolve_reference_bytes(
        "static/game/sprites/deck.png",
        output_dir=output_dir,
        generated_cache={},
    )

    assert resolved == b"fresh-bytes"


def test_select_records_by_key_returns_sprite_and_icon(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "deck.mdc"
    icon_path = tmp_path / "icons" / "deck.mdc"
    sprite_path.parent.mkdir(parents=True)
    icon_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: deck-sprite",
                "asset: static/game/sprites/deck.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )
    _write_prompt(
        icon_path,
        "\n".join(
            [
                "name: deck-icon",
                "asset: static/game/icons/deck.png",
                "model: gemini-3-pro-image",
                "reference_asset: static/game/sprites/deck.png",
                "depends_on: deck-sprite",
            ]
        ),
    )

    all_records = [
        static_assets.parse_asset_prompt(sprite_path),
        static_assets.parse_asset_prompt(icon_path),
    ]
    selected = static_assets.select_records(all_records, key="deck")

    assert [static_assets.record_kind(record) for record in selected] == ["sprite", "icon"]


def test_select_records_skips_approved_by_default(tmp_path: pathlib.Path) -> None:
    approved_path = tmp_path / "sprites" / "trainer.mdc"
    gear_path = tmp_path / "sprites" / "camera.mdc"
    approved_path.parent.mkdir(parents=True)
    _write_prompt(
        approved_path,
        "\n".join(
            [
                "name: trainer-sprite",
                "asset: static/game/sprites/trainer.png",
                "model: gemini-3-pro-image",
                "status: approved",
            ]
        ),
    )
    _write_prompt(
        gear_path,
        "\n".join(
            [
                "name: camera-sprite",
                "asset: static/game/sprites/camera.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )

    all_records = [
        static_assets.parse_asset_prompt(approved_path),
        static_assets.parse_asset_prompt(gear_path),
    ]
    selected = static_assets.select_records(all_records)

    assert [record.name for record in selected] == ["camera-sprite"]


def test_select_records_unknown_key_raises() -> None:
    with pytest.raises(ValueError, match="Unknown asset"):
        static_assets.select_records(static_assets.load_all_records(), key="not-a-real-asset")


def test_expand_with_reference_icons_adds_sprite_linked_icons(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "deck.mdc"
    icon_path = tmp_path / "icons" / "deck.mdc"
    settings_path = tmp_path / "icons" / "settings.mdc"
    sprite_path.parent.mkdir(parents=True)
    icon_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: deck-sprite",
                "asset: static/game/sprites/deck.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )
    _write_prompt(
        icon_path,
        "\n".join(
            [
                "name: deck-icon",
                "asset: static/game/icons/deck.png",
                "model: gemini-3-pro-image",
                "reference_asset: static/game/sprites/deck.png",
                "depends_on: deck-sprite",
            ]
        ),
    )
    _write_prompt(
        settings_path,
        "\n".join(
            [
                "name: settings-icon",
                "asset: static/game/icons/settings.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )

    all_records = [
        static_assets.parse_asset_prompt(sprite_path),
        static_assets.parse_asset_prompt(icon_path),
        static_assets.parse_asset_prompt(settings_path),
    ]
    sprite_only = [all_records[0]]
    expanded = static_assets.expand_with_reference_icons(sprite_only, all_records=all_records)

    assert [record.name for record in expanded] == ["deck-sprite", "deck-icon"]


def test_resolve_matte_solves_icon_key() -> None:
    deck_icon = next(record for record in static_assets.load_all_records() if record.name == "vibe-deck-icon")
    matte = static_assets.resolve_matte(deck_icon)
    assert matte.hex.startswith("#")


def test_compose_generation_prompt_injects_style_anchors(tmp_path: pathlib.Path) -> None:
    anchor_path = tmp_path / "anchors"
    anchor_path.mkdir()
    (anchor_path / "style-a.md").write_text(
        "# Style A\n\n---\nSTYLE A RULES",
        encoding="utf-8",
    )
    (anchor_path / "style-b.md").write_text(
        "# Style B\n\n---\nSTYLE B RULES",
        encoding="utf-8",
    )

    prompt_path = tmp_path / "game" / "thing.mdc"
    prompt_path.parent.mkdir(parents=True)
    _write_prompt(
        prompt_path,
        "\n".join(
            [
                "name: thing",
                "asset: static/game/thing.png",
                "model: gemini-3-pro-image",
                "style_anchors:",
                "  - style-a.md",
                "  - style-b.md",
            ]
        ),
        body="TASK — draw the thing.",
    )
    record = static_assets.parse_asset_prompt(prompt_path)

    original_dir = static_assets.STYLE_ANCHORS_DIR
    static_assets.STYLE_ANCHORS_DIR = anchor_path
    try:
        composed = static_assets.compose_generation_prompt(record)
    finally:
        static_assets.STYLE_ANCHORS_DIR = original_dir

    assert composed == "STYLE A RULES\n\nSTYLE B RULES\n\nTASK — draw the thing."


def test_resolve_matte_solves_from_gear_key(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "vibe-cart.mdc"
    sprite_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: vibe-cart-sprite",
                "asset: static/game/sprites/vibe-cart.png",
                "model: gemini-3-pro-image",
            ]
        ),
    )
    record = static_assets.parse_asset_prompt(sprite_path)
    matte = static_assets.resolve_matte(record)

    assert matte.hex.startswith("#")
    assert brand.min_foreground_separation(matte, *static_assets.GEAR_SPRITE_FOREGROUND["vibe-cart"]) > 0


def test_resolve_matte_uses_pinned_frontmatter(tmp_path: pathlib.Path) -> None:
    sprite_path = tmp_path / "sprites" / "camera.mdc"
    sprite_path.parent.mkdir(parents=True)
    _write_prompt(
        sprite_path,
        "\n".join(
            [
                "name: camera-sprite",
                "asset: static/game/sprites/camera.png",
                "model: gemini-3-pro-image",
                "matte: '#00B140'",
            ]
        ),
    )
    record = static_assets.parse_asset_prompt(sprite_path)

    assert static_assets.resolve_matte(record).hex == "#00B140"


def test_prepare_chroma_prompt_injects_matte_and_strips_white() -> None:
    matte = brand.Color("#C71585", "Chroma Magenta", "test")
    prompt = static_assets.prepare_chroma_prompt(
        "A camera. Isolated on a transparent background, presented in a static pose.",
        matte,
    )

    assert "transparent background" not in prompt.casefold()
    assert matte.hex in prompt
    assert "chroma-key background" in prompt.casefold()
    assert "solid white background" not in prompt.casefold()


def test_resolve_repo_path_keeps_absolute_paths() -> None:
    absolute = pathlib.Path("C:/tmp/out")
    assert static_assets.resolve_repo_path(absolute) == absolute
