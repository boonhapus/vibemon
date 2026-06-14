"""Regenerate hand-authored static game assets from asset-prompt records."""

from typing import Annotated
import asyncio
import datetime as dt
import json
import pathlib
import sys

import cyclopts
import pydantic_ai

from app.core.asset_paths import GENERATED_DIR
from app.domains.vibemon import brand
from app.genai import google as genai_google
from app.genai import sprite_facing, static_assets
from app.workflows import pixelsnap, sprite_postprocess
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

DEFAULT_OUTPUT_DIR = GENERATED_DIR / "assets"

app = cyclopts.App(
    help=(
        "Generate static game PNGs from vibemon/frontend/asset-prompts/game/*.mdc records.\n\n"
        "Pass an asset key (the prompt file stem) to render every record for that object —\n"
        "typically the sprite plus its HUD icon. With no key, renders every non-approved asset.\n\n"
        "Sprites and gear HUD icons use a solved chroma-key matte and trainer-style matte removal.\n\n"
        "Outputs land under <repo>/.generated/assets/ by default.\n\n"
        "Examples:\n"
        "  generate_static_assets.py\n"
        "  generate_static_assets.py vibe-deck\n"
        "  generate_static_assets.py --output .generated/assets/2026-06-09"
    )
)


def _google_model_string(model: str) -> str:
    if ":" in model:
        return model
    return f"google-gla:{model}"


def _write_manifest(output_dir: pathlib.Path, rows: list[dict[str, object]]) -> None:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": dt.datetime.now(dt.UTC).isoformat(),
                "output_dir": str(output_dir),
                "assets": rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


async def _generate_raw_image(
    record: static_assets.AssetPromptRecord,
    *,
    settings,
    reference_bytes: bytes | None = None,
) -> bytes:
    agent = genai_google.build_image_agent(_google_model_string(record.model), settings.secrets)

    composed = static_assets.compose_generation_prompt(record)
    prompt_text = composed
    if static_assets.wants_matte_key(record):
        matte = static_assets.resolve_matte(record)
        composed = static_assets.compose_generation_prompt(record)
        prompt_text = static_assets.prepare_chroma_prompt(composed, matte)
        _log(f"    matte {matte.hex} ({matte.name})")

    user_prompt: genai_google.ImagePrompt = prompt_text
    if reference_bytes is not None:
        user_prompt = [
            pydantic_ai.BinaryImage(data=reference_bytes, media_type="image/png"),
            prompt_text,
        ]

    result = await agent.run(user_prompt)
    return result.output.data


async def _generate_png(
    record: static_assets.AssetPromptRecord,
    *,
    settings,
    reference_bytes: bytes | None = None,
) -> tuple[bytes, str | None]:
    matte: brand.Color | None = None
    if static_assets.wants_matte_key(record):
        matte = static_assets.resolve_matte(record)

    raw = await _generate_raw_image(
        record,
        settings=settings,
        reference_bytes=reference_bytes,
    )

    if matte is None:
        return raw, None

    keyed = sprite_postprocess.normalize_trainer_reference_image(raw, bg_color=matte)
    rgba = pixelsnap.snap_rgba_png(keyed)
    return rgba, matte.hex


def _manifest_row(
    *,
    record: static_assets.AssetPromptRecord,
    key: str,
    kind: str,
    relative_asset: str,
    destination: pathlib.Path,
    matte_hex: str | None,
    png_bytes: int,
    derived_from: str | None = None,
) -> dict[str, object]:
    try:
        output_path = str(destination.relative_to(static_assets.REPO_ROOT))
    except ValueError:
        output_path = str(destination.resolve())
    return {
        "key": key,
        "kind": kind,
        "name": record.name,
        "asset": record.asset if derived_from is None else relative_asset,
        "output_asset": relative_asset,
        "model": record.model,
        "matte": matte_hex,
        "reference_asset": record.reference_asset,
        "depends_on": record.depends_on,
        "derived_from": derived_from,
        "prompt_path": str(record.path.relative_to(static_assets.REPO_ROOT)),
        "output_path": output_path,
        "bytes": png_bytes,
    }


@app.default
def generate_static_assets(
    name: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Asset key (prompt file stem). Generates sprite + icon when both exist.",
        ),
    ] = None,
    *,
    output: Annotated[
        pathlib.Path,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Directory root for generated PNGs.",
        ),
    ] = DEFAULT_OUTPUT_DIR,
    include_approved: Annotated[
        bool,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="When generating all assets, also regenerate records marked status: approved.",
        ),
    ] = False,
    icons_only: Annotated[
        bool,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Regenerate HUD icons only; sprite references load from static or output dir.",
        ),
    ] = False,
) -> None:
    output = static_assets.resolve_repo_path(output)
    settings = _common.load_script_settings()
    all_records = static_assets.load_all_records()
    try:
        records = static_assets.select_records(
            all_records,
            key=name,
            include_approved=include_approved,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if icons_only:
        records = [record for record in records if static_assets.record_kind(record) == "icon"]

    if not records:
        _log("No asset prompts matched. Use --include-approved to regenerate approved records.")
        return

    if name is None:
        keys_run = ", ".join(sorted({static_assets.asset_key(record) for record in records}))
        skipped = (
            len(all_records) - len([record for record in all_records if record.status != "approved"])
            if not include_approved
            else 0
        )
        skip_note = f" ({skipped} approved skipped)" if skipped else ""
        _log(f"Generating {len(records)} asset(s){skip_note}. Keys: {keys_run}")
    else:
        kinds = ", ".join(static_assets.record_kind(record) for record in records)
        _log(f"Generating {name}: {kinds}")

    rows = asyncio.run(_generate_all(records, output_dir=output, settings=settings))
    _write_manifest(output, rows)
    _common.dump({"output_dir": str(output), "assets": rows})


async def _generate_all(
    records: list[static_assets.AssetPromptRecord],
    *,
    output_dir: pathlib.Path,
    settings,
) -> list[dict[str, object]]:
    generated_cache: dict[str, bytes] = {}
    rows: list[dict[str, object]] = []
    total = len(records)

    for index, record in enumerate(records, start=1):
        key = static_assets.asset_key(record)
        kind = static_assets.record_kind(record)
        relative_asset = static_assets.normalized_asset_path(record.asset)
        _log(f"[{index}/{total}] {key} ({kind}) -> {relative_asset}")

        reference_bytes: bytes | None = None
        if record.reference_asset:
            try:
                reference_bytes = static_assets.resolve_reference_bytes(
                    record.reference_asset,
                    output_dir=output_dir,
                    generated_cache=generated_cache,
                )
            except FileNotFoundError as exc:
                raise SystemExit(str(exc)) from exc

        png, matte_hex = await _generate_png(
            record,
            settings=settings,
            reference_bytes=reference_bytes,
        )
        if record.mirror_output:
            png = static_assets.mirror_png_rgba(png)
            _log("    mirrored horizontally (mirror_output)")

        destination = output_dir / relative_asset
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(png)
        generated_cache[relative_asset] = png

        rows.append(
            _manifest_row(
                record=record,
                key=key,
                kind=kind,
                relative_asset=relative_asset,
                destination=destination,
                matte_hex=matte_hex,
                png_bytes=len(png),
            )
        )
        _log(f"    wrote {len(png):,} bytes")

    _log(f"Done. {len(rows)} manifest row(s) from {total} prompt(s) in {output_dir}")
    return rows


@app.command
def derive_poses(
    name: Annotated[
        str | None,
        cyclopts.Parameter(
            help="Gear key (camera, vibe-deck, vibe-cart). Default: all gear sprites.",
        ),
    ] = None,
    *,
    source_dir: Annotated[
        pathlib.Path,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Directory containing canonical {gear}.png source sprites.",
        ),
    ] = static_assets.STATIC_GAME_DIR / "sprites",
    output: Annotated[
        pathlib.Path,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Directory root for {gear}-left.png and {gear}-right.png outputs.",
        ),
    ] = static_assets.STATIC_GAME_DIR,
) -> None:
    """Classify canonical gear sprites and write mirrored left/right pose PNGs (no image gen)."""
    settings = _common.load_script_settings()
    gear_keys = static_assets.GEAR_SPRITE_KEYS
    if name is not None:
        if name not in gear_keys:
            known = ", ".join(gear_keys)
            raise SystemExit(f"Unknown gear key {name!r}. Known keys: {known}")
        gear_keys = (name,)

    text_agent = genai_google.build_text_agent(settings.genai.text, settings.secrets)

    async def _derive_all() -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for gear_key in gear_keys:
            source_path = source_dir / f"{gear_key}.png"
            if not source_path.is_file():
                raise SystemExit(f"Missing canonical sprite {source_path}")

            source_rgba = source_path.read_bytes()
            _log(f"deriving poses for {gear_key} from {source_path}")

            poses, detected, source_facing, source_pose = await sprite_facing.derive_gear_poses(
                gear_key,
                source_rgba,
                text_agent,
            )
            written = static_assets.write_gear_pose_pair(gear_key, poses, output_dir=output)
            for path in written:
                _log(f"    wrote {path.name} (detected={detected.value}, source={source_pose})")

            rows.append(
                {
                    "gear": gear_key,
                    "detected_facing": detected.value,
                    "source_facing": source_facing.value,
                    "source_pose": source_pose,
                    "outputs": [str(path) for path in written],
                }
            )
        return rows

    rows = asyncio.run(_derive_all())
    _common.dump({"poses": rows})


if __name__ == "__main__":
    app()
