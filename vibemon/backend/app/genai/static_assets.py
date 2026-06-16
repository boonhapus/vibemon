"""Parse and orchestrate hand-authored static game asset prompts."""

from collections.abc import Iterable
import dataclasses
import io
import pathlib
import re

import yaml

from app.core.asset_paths import (
    ASSET_PROMPTS_DIR,
    REPO_ROOT,
    STATIC_GAME_DIR,
    STYLE_ANCHORS_DIR,
)
from app.domains.vibemon import brand
from app.genai import sprite_facing

GEAR_SPRITE_KEYS: tuple[str, ...] = tuple(sprite_facing.GEAR_FACING_SUBJECTS.keys())


_WALNUT = brand.Color("#5C4033", "Walnut", "Vibe Deck wood-grain body")
_PEWTER = brand.Color("#8A8C8E", "Pewter", "Belt clip and brushed metal")
_TEAL_MIST = brand.Color("#3D8C8C", "Teal Mist", "Camera rainbow stripe accent")
_PARCHMENT = brand.Color("#F0E7CE", "Parchment Cream", "Text boxes, light fills — DESIGN.md §2.1")

# Expected foreground anchors per gear sprite key — drives chroma-key matte solving.
GEAR_SPRITE_FOREGROUND: dict[str, tuple[brand.Color, ...]] = {
    "camera": (
        _PARCHMENT,
        brand.TOBACCO_BROWN,
        brand.MUSTARD_YELLOW,
        brand.GRAPE_PLUM,
        brand.BURNT_ORANGE,
        _TEAL_MIST,
        *brand.SPRITE_CHROMA_PROTECTED_COLORS,
    ),
    "vibe-deck": (
        _WALNUT,
        _PARCHMENT,
        brand.TOBACCO_BROWN,
        brand.GRAPE_PLUM,
        brand.MUSTARD_YELLOW,
        brand.SAGE_OLIVE,
        brand.BURNT_ORANGE,
        _PEWTER,
        *brand.SPRITE_CHROMA_PROTECTED_COLORS,
    ),
    "vibe-cart": (
        _PARCHMENT,
        brand.GRAPE_PLUM,
        brand.TOBACCO_BROWN,
        brand.MUSTARD_YELLOW,
        *brand.SPRITE_CHROMA_PROTECTED_COLORS,
    ),
}

_CHROMA_BACKGROUND_RE = re.compile(
    r"(?:isolated on a (?:clean, )?(?:solid )?(?:white|transparent) background[^.]*\.?\s*)|"
    r"(?:COMPOSITION — isolated on a solid white background[^.]*\.?\s*)",
    flags=re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True, slots=True)
class AssetPromptRecord:
    path: pathlib.Path
    name: str
    asset: str
    model: str
    prompt: str
    role: str | None = None
    reference_asset: str | None = None
    depends_on: str | None = None
    status: str | None = None
    matte: str | None = None
    mirror_output: bool = False
    derived_from: str | None = None
    derive: str | None = None
    style_anchors: tuple[str, ...] = ()


def parse_asset_prompt(path: pathlib.Path) -> AssetPromptRecord:
    source = path.read_text(encoding="utf-8")
    if source.count("---\n") < 2:
        raise ValueError(f"{path} is missing YAML frontmatter")

    _, _, rest = source.partition("---\n")
    frontmatter, _, body = rest.partition("---\n")
    metadata = yaml.safe_load(frontmatter) or {}

    name = str(metadata.get("name") or path.stem)
    asset = str(metadata.get("asset") or "")
    model = str(metadata.get("model") or "")
    if not asset:
        raise ValueError(f"{path} is missing required frontmatter field 'asset'")
    if not model:
        raise ValueError(f"{path} is missing required frontmatter field 'model'")

    role = metadata.get("role")
    reference_asset = metadata.get("reference_asset")
    depends_on = metadata.get("depends_on")
    status = metadata.get("status")
    matte = metadata.get("matte")
    mirror_output = bool(metadata.get("mirror_output"))
    derived_from = metadata.get("derived_from")
    derive = metadata.get("derive")
    style_anchors = _parse_style_anchors(metadata.get("style_anchors") or metadata.get("style_anchor"))
    return AssetPromptRecord(
        path=path,
        name=name,
        asset=asset,
        model=model,
        prompt=body.strip(),
        role=str(role) if role else None,
        reference_asset=str(reference_asset) if reference_asset else None,
        depends_on=str(depends_on) if depends_on else None,
        status=str(status) if status else None,
        matte=str(matte) if matte else None,
        mirror_output=mirror_output,
        derived_from=str(derived_from) if derived_from else None,
        derive=str(derive) if derive else None,
        style_anchors=style_anchors,
    )


def _parse_style_anchors(raw: object) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(str(entry) for entry in raw)
    raise ValueError("style_anchor / style_anchors must be a string or list of strings")


def load_style_anchor_text(name: str) -> str:
    """Return the injectable prompt body from a reusable style anchor file."""
    path = STYLE_ANCHORS_DIR / name
    if not path.is_file():
        raise ValueError(f"style anchor {name!r} not found at {path}")
    source = path.read_text(encoding="utf-8")
    if "\n---\n" in source:
        _, _, injectable = source.partition("\n---\n")
        return injectable.strip()
    raise ValueError(f"style anchor {name!r} is missing injectable body after '---'")


def compose_generation_prompt(record: AssetPromptRecord) -> str:
    """Merge reusable style anchors with the idea-specific prompt body."""
    sections = [load_style_anchor_text(name) for name in record.style_anchors]
    if record.prompt:
        sections.append(record.prompt)
    if not sections:
        raise ValueError(f"{record.name} has no style anchors or prompt body")
    return "\n\n".join(sections)


_GEAR_POSE_SUFFIXES: tuple[str, ...] = ("-left", "-right")


def asset_key(record: AssetPromptRecord) -> str:
    """Prompt file stem (e.g. camera-left, vibe-deck-right)."""
    return record.path.stem


def gear_key(record: AssetPromptRecord) -> str:
    """CLI grouping key — gear id shared across poses and icons (e.g. vibe-deck)."""
    stem = record.path.stem
    for suffix in _GEAR_POSE_SUFFIXES:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def gear_pose(record: AssetPromptRecord) -> str | None:
    stem = record.path.stem
    if stem.endswith("-left"):
        return "left"
    if stem.endswith("-right"):
        return "right"
    return None


def is_mirror_derived(record: AssetPromptRecord) -> bool:
    return record.derive == "mirror_horizontal" and record.derived_from is not None


def record_kind(record: AssetPromptRecord) -> str:
    if "backgrounds" in record.path.parts:
        return "background"
    if record.reference_asset is not None:
        return "icon"
    if "icons" in record.path.parts:
        return "icon"
    return "sprite"


def known_asset_keys(records: list[AssetPromptRecord]) -> tuple[str, ...]:
    return tuple(sorted({gear_key(record) for record in records}))


def load_all_records(prompts_dir: pathlib.Path = ASSET_PROMPTS_DIR) -> list[AssetPromptRecord]:
    return [parse_asset_prompt(path) for path in sorted(prompts_dir.rglob("*.mdc"))]


def match_records_by_key(all_records: list[AssetPromptRecord], key: str) -> list[AssetPromptRecord]:
    normalized = key.strip()
    if not normalized:
        raise ValueError("asset key is empty")

    by_gear = [record for record in all_records if gear_key(record) == normalized]
    if by_gear:
        return by_gear

    by_stem = [record for record in all_records if asset_key(record) == normalized]
    if by_stem:
        return by_stem

    by_name = [record for record in all_records if record.name == normalized]
    if by_name:
        return by_name

    known = ", ".join(known_asset_keys(all_records))
    raise ValueError(f"Unknown asset {normalized!r}. Known keys: {known}")


def expand_with_reference_icons(
    selected: list[AssetPromptRecord],
    *,
    all_records: list[AssetPromptRecord],
) -> list[AssetPromptRecord]:
    """When sprites are in the batch, include HUD icons that reference them."""
    selected_names = {record.name for record in selected}
    sprite_output_paths = {
        normalized_asset_path(record.asset) for record in selected if record_kind(record) == "sprite"
    }
    if not sprite_output_paths:
        return selected

    extra: list[AssetPromptRecord] = []
    for record in all_records:
        if record.name in selected_names:
            continue
        if record_kind(record) != "icon":
            continue
        ref_path = normalized_asset_path(record.reference_asset) if record.reference_asset else None
        if ref_path in sprite_output_paths or (record.depends_on is not None and record.depends_on in selected_names):
            extra.append(record)

    if not extra:
        return selected

    merged = list(selected)
    for record in extra:
        selected_names.add(record.name)
        merged.append(record)
    return merged


def select_records(
    all_records: list[AssetPromptRecord],
    *,
    key: str | None = None,
    include_approved: bool = False,
) -> list[AssetPromptRecord]:
    """Resolve a CLI key to sprites plus any icons that reference them."""
    if key is None:
        pool = all_records
        if not include_approved:
            pool = [record for record in all_records if record.status != "approved"]
    else:
        pool = expand_with_dependencies(
            match_records_by_key(all_records, key),
            all_records=all_records,
        )

    pool = expand_with_dependencies(pool, all_records=all_records)
    pool = expand_with_reference_icons(pool, all_records=all_records)
    return sort_for_generation(pool)


def expand_with_dependencies(
    selected: Iterable[AssetPromptRecord],
    *,
    all_records: list[AssetPromptRecord],
) -> list[AssetPromptRecord]:
    """Return selected records plus any `depends_on` chain, ordered for generation."""
    by_name = {record.name: record for record in all_records}
    ordered_names: list[str] = []
    seen: set[str] = set()

    def visit(name: str) -> None:
        if name in seen:
            return
        record = by_name.get(name)
        if record is None:
            raise ValueError(f"depends_on {name!r} is not a known asset-prompt name")
        if record.depends_on:
            visit(record.depends_on)
        seen.add(name)
        ordered_names.append(name)

    for record in selected:
        visit(record.name)

    return [by_name[name] for name in ordered_names]


def sort_for_generation(records: list[AssetPromptRecord]) -> list[AssetPromptRecord]:
    """Sprites and standalone assets before reference-linked icon passes."""
    without_reference = [record for record in records if record.reference_asset is None]
    with_reference = [record for record in records if record.reference_asset is not None]
    return without_reference + with_reference


def resolve_repo_path(path: pathlib.Path) -> pathlib.Path:
    """Resolve repo-root-relative paths such as ``.generated/assets``."""
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == ".generated":
        return REPO_ROOT / path
    return path


def normalized_asset_path(asset: str) -> str:
    """Mirror vibemon/frontend/static/game/... regardless of frontmatter prefix."""
    path = pathlib.PurePosixPath(asset)
    parts = path.parts
    if parts[:2] == ("static", "game"):
        return str(pathlib.PurePosixPath("game", *parts[2:]))
    if parts[:1] == ("game",):
        return str(path)
    return asset


def static_game_path(relative_asset: str) -> pathlib.Path:
    return STATIC_GAME_DIR / pathlib.Path(normalized_asset_path(relative_asset)).relative_to("game")


def resolve_reference_bytes(
    reference_asset: str,
    *,
    output_dir: pathlib.Path,
    generated_cache: dict[str, bytes],
) -> bytes:
    relative = normalized_asset_path(reference_asset)
    if relative in generated_cache:
        return generated_cache[relative]

    generated_path = output_dir / relative
    if generated_path.is_file():
        return generated_path.read_bytes()

    committed_path = static_game_path(reference_asset)
    if committed_path.is_file():
        return committed_path.read_bytes()

    raise FileNotFoundError(f"Reference asset {reference_asset!r} not found at {generated_path} or {committed_path}")


def wants_matte_key(record: AssetPromptRecord) -> bool:
    return record_kind(record) in ("sprite", "icon")


def resolve_matte(record: AssetPromptRecord) -> brand.Color:
    """Pick or load the chroma-key matte for a sprite or gear HUD icon."""
    if record.matte:
        return brand.Color(record.matte.upper(), "Pinned matte", f"asset-prompt {record.name}")

    key = gear_key(record)
    foreground = GEAR_SPRITE_FOREGROUND.get(key)
    if foreground is None:
        raise ValueError(
            f"No matte solver configured for asset key {key!r}. Add foreground anchors or pin matte in frontmatter."
        )
    return brand.solve_background_color(*foreground, hue_protected=foreground)


def mirror_png_rgba(image: bytes) -> bytes:
    """Mirror a keyed RGBA PNG horizontally (e.g. HUD icon facing correction)."""
    from PIL import Image, ImageOps

    mirrored = ImageOps.mirror(Image.open(io.BytesIO(image)).convert("RGBA"))
    out = io.BytesIO()
    mirrored.save(out, format="PNG")
    return out.getvalue()


def prepare_chroma_prompt(prompt: str, matte: brand.Color) -> str:
    """Strip white/transparent clauses and inject a flat chroma matte canvas rule."""
    cleaned = _CHROMA_BACKGROUND_RE.sub("", prompt).strip()
    matte_clause = (
        f"CANVAS — flat matte chroma-key background {matte.hex} as ONE uniform wash "
        f"filling every pixel that is not an icon. The background must stay perfectly "
        f"flat with no texture, grain, vignette, or dither on the matte. "
        f"NEVER use Parchment Cream, white, beige, or any icon fill color as the sheet background — "
        f"only {matte.hex}. Icon body fills are Parchment Cream (#F0E7CE) and must stay visually "
        f"distinct from the matte. No scenery, floor line, drop shadow, contact shadow, or props "
        f"outside the icons. Generous empty matte spacing between icons."
    )
    return f"{cleaned}\n\n{matte_clause}"


def gear_canonical_sprite_path(gear_key: str) -> pathlib.Path:
    return STATIC_GAME_DIR / "sprites" / f"{gear_key}.png"


def gear_pose_sprite_path(gear_key: str, pose: sprite_facing.GearPoseLabel) -> pathlib.Path:
    return STATIC_GAME_DIR / "sprites" / f"{gear_key}-{pose}.png"


def write_gear_pose_pair(
    gear_key: str,
    poses: dict[sprite_facing.GearPoseLabel, bytes],
    *,
    output_dir: pathlib.Path,
) -> list[pathlib.Path]:
    written: list[pathlib.Path] = []
    for pose, png in poses.items():
        destination = output_dir / "sprites" / f"{gear_key}-{pose}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(png)
        written.append(destination)
    return written
