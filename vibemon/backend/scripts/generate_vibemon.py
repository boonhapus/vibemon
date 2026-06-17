"""Rehearse creating a Vibemon at a chosen UX stage."""

from typing import Annotated, Any, Literal
import asyncio
import datetime as dt
import enum
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.core.time import resolve_clock
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.schema import PublicAsset, PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.providers import registry
from app.providers.base import VibeProvider
from app.storage.database import mapper, vibemon_repo
from app.storage.secrets.repository import DbTrainerSecrets
from app.workflows import birth_persist, public_projection
from app.workflows import candidate as candidate_workflow
from app.workflows import generate_wild_supply as wild_workflow
from app.workflows.materialize_vibemon import MaterializeVibemon
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
SEED_OPTIONS = cyclopts.Group("Seed options", sort_key=1)
OUTPUT_OPTIONS = cyclopts.Group("Output options", sort_key=2)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=3)

app = cyclopts.App(
    help=(
        "Create Vibemon for local rehearsal with selectable birth providers.\n\n"
        "Start with a stage, then add only the story details you care about.\n"
        "Examples:\n"
        "  generate_vibemon.py\n"
        "  generate_vibemon.py --form manifested --nickname Mochi\n"
        "  generate_vibemon.py --provider climate --provider biome --provider music --trainer <uuid>\n"
        "  generate_vibemon.py --provider music --trainer <uuid> --affinity-only --location 41.88,-87.63\n"
        "  generate_vibemon.py --count 5 --form christened --output table\n"
        "  generate_vibemon.py --stage candidate --trainer <uuid> --form manifested"
    )
)


class GenerationStage(enum.StrEnum):
    CANDIDATE = "candidate"
    WILD = "wild"
    OWNED = "owned"


@app.default
def generate_vibemon(
    *,
    stage: Annotated[
        GenerationStage | None,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Optional UX flow destination: candidate, wild, or owned. Omit for a plain birth.",
        ),
    ] = None,
    form: Annotated[
        VibemonLifecycleT,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help=(
                "Asset completeness: born (identity only), christened (+ reference image), "
                "or manifested (+ sprite sheet)."
            ),
        ),
    ] = VibemonLifecycleT.BORN,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID for candidate, owned, or music birth."),
    ] = None,
    name: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer name to create when the trainer is new."),
    ] = None,
    nickname: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional Vibemon nickname."),
    ] = None,
    location: Annotated[
        str | None,
        cyclopts.Parameter(group=SEED_OPTIONS, help="Birth location as 'latitude,longitude'; random if omitted."),
    ] = None,
    born_at: Annotated[
        str | None,
        cyclopts.Parameter(group=SEED_OPTIONS, help="Birth time as an ISO timestamp; now if omitted."),
    ] = None,
    provider: Annotated[
        list[registry.ProviderName],
        cyclopts.Parameter(
            group=SEED_OPTIONS,
            name=["--provider"],
            help="Birth providers to include (repeatable). Default: climate and biome.",
            negative_iterable=(),
        ),
    ]
    | None = None,
    affinity_only: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            negative="",
            help=("Print provider affinities and the merged birth preview without creating a persisted Vibemon."),
        ),
    ] = False,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
    asset_store_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Asset store URL override; defaults to VIBEMON_STORAGE__ASSETS.",
        ),
    ] = None,
    bust_cache: Annotated[bool, _common.bust_cache_parameter(ADVANCED_OPTIONS)] = False,
    bypass_credits: Annotated[
        bool,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, negative="", help="Skip trainer generation credit checks."),
    ] = True,
    count: Annotated[
        int,
        cyclopts.Parameter(group=OUTPUT_OPTIONS, help="How many random Vibemon to create."),
    ] = 1,
    output: Annotated[
        Literal["json", "table"] | None,
        cyclopts.Parameter(group=OUTPUT_OPTIONS, help="Print JSON or a markdown table; table when count > 1."),
    ] = None,
) -> None:
    storage = _common.load_script_settings(
        database_url=database_url,
        asset_store_url=asset_store_url,
        bust_cache=bust_cache,
    )
    provider_names = registry.resolve_provider_names(provider or None)
    _common.require_trainer_for_music(provider_names, trainer_id=trainer)

    if count < 1:
        raise SystemExit("--count must be at least 1.")
    if affinity_only:
        if count > 1:
            raise SystemExit("--affinity-only cannot be combined with --count > 1.")
        if stage is not None:
            raise SystemExit("--affinity-only cannot be combined with --stage.")
    elif count > 1 and form is VibemonLifecycleT.BORN:
        raise SystemExit(
            "--form must be christened or manifested when --count > 1 (reference images require christening)."
        )

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
            form=form,
            database_url=storage.storage.database,
            asset_store_url=storage.storage.assets,
            nickname=nickname,
            bypass_credits=bypass_credits,
            provider_names=provider_names,
            affinity_only=affinity_only,
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
    stage: GenerationStage | None,
    trainer_id: uuid.UUID | None,
    username: str | None,
    latitude: float | None,
    longitude: float | None,
    timestamp: str | None,
    form: VibemonLifecycleT,
    nickname: str | None,
    bypass_credits: bool,
    provider_names: tuple[registry.ProviderName, ...],
) -> tuple[float, float, PublicVibemon, tuple[generation_types.ProviderWarning, ...]]:
    result: PublicVibemon | None = None
    provider_notes: tuple[generation_types.ProviderWarning, ...] = ()
    item_latitude = 0.0
    item_longitude = 0.0
    providers = registry.build_provider_instances(provider_names)
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
            trainer_id=trainer_id or _common.SCRIPT_ANONYMOUS_TRAINER_ID,
            providers=providers,
        )
        try:
            if stage is None:
                result, provider_notes = await _generate_plain_vibemon(
                    sess,
                    seed=seed,
                    form=form,
                    nickname=nickname,
                )
            elif stage is GenerationStage.WILD:
                result = await wild_workflow.generate_wild_supply(
                    sess,
                    birth_seed=seed,
                    nickname=nickname,
                    christen=form is not VibemonLifecycleT.BORN,
                )
                if form is VibemonLifecycleT.MANIFESTED:
                    result = await _materialize_vibemon(sess, result.id, lifecycle=form)
            else:
                result = await _generate_trainer_stage(
                    sess,
                    seed=seed,
                    stage=stage,
                    trainer_id=trainer_id or uuid.uuid7(),
                    username=username,
                    form=form,
                    nickname=nickname,
                    bypass_credits=bypass_credits,
                )
            break
        except IndexError, OSError:
            if attempt == 4:
                raise
            continue
    if result is None:
        raise RuntimeError("Failed to generate Vibemon.")
    return item_latitude, item_longitude, result, _provider_notes(result, fallback=provider_notes)


async def _run(
    *,
    stage: GenerationStage | None,
    trainer_id: uuid.UUID | None,
    username: str | None,
    latitude: float | None,
    longitude: float | None,
    timestamp: str | None,
    form: VibemonLifecycleT,
    database_url: str,
    asset_store_url: str,
    nickname: str | None,
    bypass_credits: bool,
    provider_names: tuple[registry.ProviderName, ...],
    affinity_only: bool,
    count: int,
    output: Literal["json", "table"],
) -> None:
    _common.ensure_local_blob_dir(asset_store_url)

    if affinity_only:
        payload = await _provider_affinities(
            database_url=database_url,
            trainer_id=trainer_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            provider_names=provider_names,
            nickname=nickname,
        )
        _print_merged_vibemon_summary(payload)
        _common.dump(payload)
        return

    providers = registry.build_provider_instances(provider_names)
    rows: list[dict[str, object]] = []
    item_database_url = database_url
    batch_coords = _batch_birth_coords(count) if count > 1 and latitude is None and longitude is None else None

    for index in range(count):
        item_latitude = latitude
        item_longitude = longitude
        if batch_coords is not None:
            item_latitude, item_longitude = batch_coords[index]
        async with _common.session_scope(database_url=item_database_url) as sess:
            item_latitude, item_longitude, result, provider_notes = await _generate_one(
                sess,
                stage=stage,
                trainer_id=trainer_id,
                username=username,
                latitude=item_latitude,
                longitude=item_longitude,
                timestamp=timestamp,
                form=form,
                nickname=nickname,
                bypass_credits=bypass_credits,
                provider_names=provider_names,
            )
        rows.append(
            {
                "index": index + 1,
                "latitude": item_latitude,
                "longitude": item_longitude,
                "provider_notes": provider_notes,
                "vibemon": result,
            }
        )

    if output == "table":
        _print_table(rows, stage=stage, form=form, providers=providers)
        return

    if count == 1:
        row = rows[0]
        payload: dict[str, object] = {
            "form": form.value,
            "providers": [provider.name for provider in providers],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "vibemon": row["vibemon"],
        }
        if stage is not None:
            payload["stage"] = stage.value
        if row["provider_notes"]:
            payload["provider_notes"] = row["provider_notes"]
        _common.dump(payload)
        return

    batch_payload: dict[str, object] = {
        "form": form.value,
        "providers": [provider.name for provider in providers],
        "vibemon": rows,
    }
    if stage is not None:
        batch_payload["stage"] = stage.value
    _common.dump(batch_payload)


async def _provider_affinities(
    *,
    database_url: str,
    trainer_id: uuid.UUID | None,
    latitude: float | None,
    longitude: float | None,
    timestamp: str | None,
    provider_names: tuple[registry.ProviderName, ...],
    nickname: str | None,
) -> dict[str, object]:
    item_latitude, item_longitude = (
        (latitude, longitude) if latitude is not None and longitude is not None else _random_birth_coords()
    )
    seed = BirthSeed(
        timestamp=_common.parse_datetime(timestamp) if timestamp is not None else dt.datetime.now(tz=dt.UTC),
        geo_coords=(item_latitude, item_longitude),
        trainer_id=trainer_id or _common.SCRIPT_ANONYMOUS_TRAINER_ID,
        providers=registry.build_provider_instances(provider_names),
    )
    affinity_rows: list[dict[str, object]] = []
    resolved_affinities: list[Affinity] = []
    async with _common.session_scope(database_url=database_url) as sess:
        if trainer_id is not None:
            await _common.ensure_trainer(sess, trainer_id)
        secrets = DbTrainerSecrets(sess)
        for provider in seed.providers:
            assert isinstance(provider, VibeProvider)
            payload = await provider.fetch(seed, secrets=secrets)
            affinity = await provider.synthesize(seed, payload)
            resolved_affinities.append(affinity)
            affinity_rows.append(
                {
                    "provider": provider.name,
                    "provider_notes": affinity.provider_notes,
                    "affinity": _affinity_payload(affinity),
                }
            )

    vibemon = Vibemon.birth(
        *resolved_affinities,
        birth_seed=seed,
        nickname=nickname,
    )
    provider_notes = Affinity.collect_notes(*resolved_affinities)

    return {
        "latitude": item_latitude,
        "longitude": item_longitude,
        "providers": [provider.name for provider in seed.providers],
        "affinities": affinity_rows,
        "provider_notes": provider_notes,
        "vibemon": vibemon,
    }


async def _load_public_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> PublicVibemon:
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    return await public_projection.public_vibemon(row)


async def _materialize_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    lifecycle: VibemonLifecycleT,
) -> PublicVibemon:
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    if lifecycle is VibemonLifecycleT.CHRISTENED:
        vibemon = await MaterializeVibemon().christen(vibemon)
    elif lifecycle is VibemonLifecycleT.MANIFESTED:
        vibemon = await MaterializeVibemon().christen_and_manifest(vibemon)
    mapper.apply_vibemon_to_row(row, vibemon)
    await vibemon_repo.persist_assets(sess, vibemon)
    await sess.flush()
    return await public_projection.public_vibemon(row)


async def _generate_plain_vibemon(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    form: VibemonLifecycleT,
    nickname: str | None,
) -> tuple[PublicVibemon, tuple[generation_types.ProviderWarning, ...]]:
    await _common.ensure_trainer(sess, seed.trainer_id)
    row, provider_notes = await birth_persist.birth_and_persist_vibemon(
        sess,
        birth_seed=seed,
        nickname=nickname,
        now=resolve_clock(),
        christen=form is not VibemonLifecycleT.BORN,
    )
    if form is VibemonLifecycleT.MANIFESTED:
        return await _materialize_vibemon(sess, row.id, lifecycle=VibemonLifecycleT.MANIFESTED), provider_notes
    await sess.flush()
    return await _load_public_vibemon(sess, row.id), provider_notes


async def _generate_trainer_stage(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    stage: GenerationStage,
    trainer_id: uuid.UUID,
    username: str | None,
    form: VibemonLifecycleT,
    nickname: str | None,
    bypass_credits: bool,
) -> PublicVibemon:
    await _common.ensure_trainer(sess, trainer_id, username=username)
    candidate = await candidate_workflow.generate_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        birth_seed=seed,
        nickname=nickname,
        bypass_credits=bypass_credits,
        christen=form is not VibemonLifecycleT.BORN,
    )
    if stage is GenerationStage.CANDIDATE:
        if form is VibemonLifecycleT.MANIFESTED:
            return await _materialize_vibemon(sess, candidate.id, lifecycle=form)
        return await _load_public_vibemon(sess, candidate.id)
    return await candidate_workflow.adopt_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        vibemon_id=candidate.id,
        manifest=form is VibemonLifecycleT.MANIFESTED,
    )


def _provider_notes(
    vibemon: PublicVibemon,
    *,
    fallback: tuple[generation_types.ProviderWarning, ...] = (),
) -> tuple[generation_types.ProviderWarning, ...]:
    review_notes = vibemon.candidate_review.provider_notes if vibemon.candidate_review is not None else ()
    return review_notes or fallback


def _affinity_payload(affinity: Affinity) -> dict[str, object]:
    identity = affinity.identity
    base = identity.base
    return {
        "elements": [element.value for element in identity.elements],
        "stats": {
            "hp": base.hp,
            "attack": base.attack,
            "defense": base.defense,
            "sp_attack": base.sp_attack,
            "sp_defense": base.sp_defense,
            "speed": base.speed,
        },
        "intensity": affinity.intensity,
        "visual_notes": affinity.visual_notes,
        "element_rankings": {element.value: score for element, score in affinity.element_rankings.items()},
        "moves": [move.id for move in affinity.moves],
    }


def _format_stats_from_identity(identity: PublicVibemon | Vibemon) -> str:
    base = identity.identity.base
    return f"{base.hp}/{base.attack}/{base.defense}/{base.sp_attack}/{base.sp_defense}/{base.speed}"


def _format_types_from_identity(vibemon: PublicVibemon | Vibemon) -> str:
    return "/".join(element.value for element in vibemon.identity.elements)


def _print_merged_vibemon_summary(payload: dict[str, object]) -> None:
    vibemon = payload.get("vibemon")
    if not isinstance(vibemon, Vibemon):
        return

    latitude = payload["latitude"]
    longitude = payload["longitude"]
    assert isinstance(latitude, float)
    assert isinstance(longitude, float)

    moves = ", ".join(move.id for move in vibemon.moves) or "—"
    print(f"\nMerged Vibemon: {vibemon.name} ({_format_types_from_identity(vibemon)})")
    print(f"  location: {latitude:.4f}, {longitude:.4f}")
    print(f"  stats:    {_format_stats_from_identity(vibemon)}")
    print(f"  moves:    {moves}")

    provider_notes = payload.get("provider_notes")
    if isinstance(provider_notes, tuple):
        codes = ", ".join(note.code for note in provider_notes if isinstance(note, generation_types.ProviderWarning))
        print(f"  notes:    {codes}")


def _format_types(vibemon: PublicVibemon) -> str:
    return _format_types_from_identity(vibemon)


def _format_stats(vibemon: PublicVibemon) -> str:
    return _format_stats_from_identity(vibemon)


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
    stage: GenerationStage | None,
    form: VibemonLifecycleT,
    providers: list[VibeProvider[Any]],
) -> None:
    provider_names = ", ".join(provider.name for provider in providers)
    stage_label = stage.value if stage is not None else "plain birth"
    print(f"Generated {len(rows)} Vibemon at `{stage_label}` / `{form.value}` via {provider_names}.\n")
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
