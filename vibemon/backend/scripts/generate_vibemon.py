"""Rehearse creating a Vibemon at a chosen UX stage."""

from __future__ import annotations

from typing import Annotated, Literal
import asyncio
import datetime as dt
import enum
import os
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.core.time import resolve_clock
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.schema import PublicAsset, PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.providers.biome.provider import BiomeProvider
from app.providers.climate.provider import ClimateProvider
from app.workflows import _workflow_support as workflow_support
from app.workflows import candidate as candidate_workflow
from app.workflows import generate_wild_supply as wild_workflow
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

app = cyclopts.App(
    help=(
        "Create Vibemon for local rehearsal using ClimateProvider + BiomeProvider.\n\n"
        "Start with a stage, then add only the story details you care about.\n"
        "Examples:\n"
        "  generate_vibemon.py\n"
        "  generate_vibemon.py manifested --nickname Mochi\n"
        "  generate_vibemon.py --count 5 --stage christened --output table\n"
        "  generate_vibemon.py owned --trainer 0198... --name Ada --form manifested"
    )
)


class GenerationStage(enum.StrEnum):
    BORN = "born"
    CHRISTENED = "christened"
    MANIFESTED = "manifested"
    CANDIDATE = "candidate"
    WILD = "wild"
    OWNED = "owned"


@app.default
def generate_vibemon(
    *,
    stage: Annotated[
        GenerationStage,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Where in the UX flow this Vibemon should be created."),
    ] = GenerationStage.BORN,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID for candidate or owned stages."),
    ] = None,
    name: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer name to create when the trainer is new."),
    ] = None,
    nickname: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional Vibemon nickname."),
    ] = None,
    idea: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional creative identity seed."),
    ] = None,
    lifecycle: Annotated[
        VibemonLifecycleT | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Visual completeness for candidate, wild, or owned stages."),
    ] = None,
    location: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Birth location as 'latitude,longitude'; random if omitted."),
    ] = None,
    born_at: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Birth time as an ISO timestamp; now if omitted."),
    ] = None,
    database_url: Annotated[
        str,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Database URL for persisted script output."),
    ] = _common.default_database_url(),
    asset_store_url: Annotated[
        str,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Blob/object store URL for generated assets."),
    ] = _common.DEFAULT_ASSET_STORE_URL,
    bypass_credits: Annotated[
        bool,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, negative="", help="Skip trainer generation credit checks."),
    ] = True,
    count: Annotated[
        int,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="How many random Vibemon to create."),
    ] = 1,
    output: Annotated[
        Literal["json", "table"] | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Print JSON or a markdown table; table when count > 1."),
    ] = None,
) -> None:
    _common.load_repo_env()
    if count < 1:
        raise SystemExit("--count must be at least 1.")
    if count > 1 and stage is GenerationStage.BORN:
        raise SystemExit("--stage must be christened or later when --count > 1 (reference images require christening).")

    resolved_output = output or ("table" if count > 1 else "json")
    latitude, longitude = _resolve_location(location=location) if location is not None else (None, None)

    asyncio.run(
        _run(
            stage=stage,
            trainer_id=trainer,
            username=name,
            latitude=latitude,
            longitude=longitude,
            timestamp=born_at,
            lifecycle=lifecycle or VibemonLifecycleT.BORN,
            database_url=database_url,
            asset_store_url=asset_store_url,
            nickname=nickname,
            core_identity=idea,
            bypass_credits=bypass_credits,
            count=count,
            output=resolved_output,
        )
    )


def _resolve_location(*, location: str | None) -> tuple[float, float]:
    if location is None:
        return _random_birth_coords()

    try:
        raw_latitude, raw_longitude = location.split(",", maxsplit=1)
        return float(raw_latitude.strip()), float(raw_longitude.strip())
    except ValueError as exc:
        raise SystemExit("--location must look like '37.7749,-122.4194'.") from exc


def _random_birth_coords() -> tuple[float, float]:
    """Pick coordinates where biome raster sampling is reliable."""
    return random.uniform(-60.0, 60.0), _common.random_longitude()


_SAMPLE_LOCATIONS: tuple[tuple[float, float], ...] = (
    (-3.4653, -62.2159),
    (51.5074, -0.1278),
    (39.8283, -98.5795),
    (23.4162, 25.6628),
    (45.4408, 12.3155),
    (-18.2871, 147.6992),
    (21.9497, 89.1833),
    (41.8781, -87.6298),
    (40.7074, -74.0113),
    (33.0198, -96.6989),
    (37.7749, -122.4194),
    (35.6762, 139.6503),
    (-33.8688, 151.2093),
    (19.4326, -99.1332),
    (-23.5505, -46.6333),
)


def _batch_birth_coords(count: int) -> list[tuple[float, float]]:
    pool = list(_SAMPLE_LOCATIONS)
    random.shuffle(pool)
    if count <= len(pool):
        return pool[:count]
    coords = pool[:]
    while len(coords) < count:
        coords.append(random.choice(_SAMPLE_LOCATIONS))
    return coords


async def _generate_one(
    sess: AsyncSession,
    *,
    stage: GenerationStage,
    trainer_id: uuid.UUID | None,
    username: str | None,
    latitude: float | None,
    longitude: float | None,
    timestamp: str | None,
    lifecycle: VibemonLifecycleT,
    nickname: str | None,
    core_identity: str | None,
    bypass_credits: bool,
    providers: list[ClimateProvider | BiomeProvider],
) -> tuple[float, float, PublicVibemon]:
    result: PublicVibemon | None = None
    item_latitude = 0.0
    item_longitude = 0.0
    for attempt in range(5):
        if latitude is not None and longitude is not None:
            item_latitude, item_longitude = latitude, longitude
        elif latitude is not None:
            item_latitude, item_longitude = latitude, _common.random_longitude()
        elif longitude is not None:
            item_latitude, item_longitude = random.uniform(-60.0, 60.0), longitude
        else:
            item_latitude, item_longitude = _random_birth_coords()
        seed = BirthSeed(
            timestamp=_common.parse_datetime(timestamp) if timestamp is not None else dt.datetime.now(tz=dt.UTC),
            geo_coords=(item_latitude, item_longitude),
            providers=providers,
        )
        try:
            if stage in (GenerationStage.BORN, GenerationStage.CHRISTENED, GenerationStage.MANIFESTED):
                result = await _generate_plain_vibemon(
                    sess,
                    seed=seed,
                    stage=stage,
                    nickname=nickname,
                    core_identity=core_identity,
                )
            elif stage is GenerationStage.WILD:
                result = await wild_workflow.generate_wild_supply(
                    sess,
                    birth_seed=seed,
                    nickname=nickname,
                    core_identity=core_identity,
                    christen=lifecycle is not VibemonLifecycleT.BORN,
                )
                if lifecycle is VibemonLifecycleT.MANIFESTED:
                    result = await _common.materialize_vibemon(sess, result.id, lifecycle=lifecycle)
            else:
                result = await _generate_trainer_stage(
                    sess,
                    seed=seed,
                    stage=stage,
                    trainer_id=trainer_id or uuid.uuid7(),
                    username=username,
                    lifecycle=lifecycle,
                    nickname=nickname,
                    core_identity=core_identity,
                    bypass_credits=bypass_credits,
                )
            break
        except IndexError, OSError:
            if attempt == 4:
                raise
            continue
    if result is None:
        raise RuntimeError("Failed to generate Vibemon.")
    return item_latitude, item_longitude, result


async def _run(
    *,
    stage: GenerationStage,
    trainer_id: uuid.UUID | None,
    username: str | None,
    latitude: float | None,
    longitude: float | None,
    timestamp: str | None,
    lifecycle: VibemonLifecycleT,
    database_url: str,
    asset_store_url: str,
    nickname: str | None,
    core_identity: str | None,
    bypass_credits: bool,
    count: int,
    output: Literal["json", "table"],
) -> None:
    os.environ["ASSET_STORE_URL"] = asset_store_url
    _common.ensure_local_blob_dir(asset_store_url)
    providers = [ClimateProvider(), BiomeProvider()]
    rows: list[dict[str, object]] = []
    item_database_url = database_url
    batch_coords = _batch_birth_coords(count) if count > 1 and latitude is None and longitude is None else None

    for index in range(count):
        item_latitude = latitude
        item_longitude = longitude
        if batch_coords is not None:
            item_latitude, item_longitude = batch_coords[index]
        async with _common.session_scope(database_url=item_database_url) as sess:
            item_latitude, item_longitude, result = await _generate_one(
                sess,
                stage=stage,
                trainer_id=trainer_id,
                username=username,
                latitude=item_latitude,
                longitude=item_longitude,
                timestamp=timestamp,
                lifecycle=lifecycle,
                nickname=nickname,
                core_identity=core_identity,
                bypass_credits=bypass_credits,
                providers=providers,
            )
        rows.append(
            {
                "index": index + 1,
                "latitude": item_latitude,
                "longitude": item_longitude,
                "vibemon": result,
            }
        )

    if output == "table":
        _print_table(rows, stage=stage, providers=providers)
        return

    if count == 1:
        row = rows[0]
        _common.dump(
            {
                "stage": stage.value,
                "providers": [provider.name for provider in providers],
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "vibemon": row["vibemon"],
            }
        )
        return

    _common.dump(
        {
            "stage": stage.value,
            "providers": [provider.name for provider in providers],
            "vibemon": rows,
        }
    )


async def _generate_plain_vibemon(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    stage: GenerationStage,
    nickname: str | None,
    core_identity: str | None,
) -> PublicVibemon:
    row = await workflow_support.birth_and_persist_vibemon(
        sess,
        birth_seed=seed,
        nickname=nickname,
        core_identity=core_identity,
        now=resolve_clock(),
        christen=stage is not GenerationStage.BORN,
    )
    if stage is GenerationStage.MANIFESTED:
        return await _common.materialize_vibemon(sess, row.id, lifecycle=VibemonLifecycleT.MANIFESTED)
    await sess.flush()
    return await _common.load_public_vibemon(sess, row.id)


async def _generate_trainer_stage(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    stage: GenerationStage,
    trainer_id: uuid.UUID,
    username: str | None,
    lifecycle: VibemonLifecycleT,
    nickname: str | None,
    core_identity: str | None,
    bypass_credits: bool,
) -> PublicVibemon:
    await _common.ensure_trainer(sess, trainer_id, username=username)
    candidate = await candidate_workflow.generate_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        birth_seed=seed,
        nickname=nickname,
        core_identity=core_identity,
        bypass_credits=bypass_credits,
        christen=lifecycle is not VibemonLifecycleT.BORN,
    )
    if stage is GenerationStage.CANDIDATE:
        if lifecycle is VibemonLifecycleT.MANIFESTED:
            await _common.materialize_vibemon(sess, candidate.id, lifecycle=lifecycle)
        return await _common.load_public_vibemon(sess, candidate.id)
    return await candidate_workflow.adopt_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        vibemon_id=candidate.id,
        manifest=lifecycle is VibemonLifecycleT.MANIFESTED,
    )


def _format_types(vibemon: PublicVibemon) -> str:
    return "/".join(element.value for element in vibemon.identity.elements)


def _format_stats(vibemon: PublicVibemon) -> str:
    identity = vibemon.identity
    return (
        f"{identity.base_hp}/{identity.base_attack}/{identity.base_defense}/"
        f"{identity.base_sp_attack}/{identity.base_sp_defense}/{identity.base_speed}"
    )


def _reference_asset(vibemon: PublicVibemon) -> PublicAsset | None:
    for asset in vibemon.assets:
        if asset.kind is AssetKind.REFERENCE:
            return asset
    return None


def _format_reference(vibemon: PublicVibemon) -> str:
    asset = _reference_asset(vibemon)
    if asset is None:
        return "—"
    return f"![{vibemon.name}]({asset.url})"


def _print_table(
    rows: list[dict[str, object]],
    *,
    stage: GenerationStage,
    providers: list[ClimateProvider | BiomeProvider],
) -> None:
    provider_names = ", ".join(provider.name for provider in providers)
    print(f"Generated {len(rows)} Vibemon at stage `{stage.value}` via {provider_names}.\n")
    headers = ("#", "name", "types", "location", "stats", "reference")
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        vibemon = row["vibemon"]
        assert isinstance(vibemon, PublicVibemon)
        latitude = row["latitude"]
        longitude = row["longitude"]
        assert isinstance(latitude, float)
        assert isinstance(longitude, float)
        print(
            f"| {row['index']} "
            f"| {vibemon.name} "
            f"| {_format_types(vibemon)} "
            f"| {latitude:.4f}, {longitude:.4f} "
            f"| {_format_stats(vibemon)} "
            f"| {_format_reference(vibemon)} |"
        )


if __name__ == "__main__":
    app()
