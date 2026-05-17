# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "vibemon-backend",
#   "geonamescache",
#   "sqlalchemy[asyncio]",
#   "aiosqlite",
# ]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
import argparse
import asyncio
import datetime as dt
import enum
import logging
import pathlib
import random

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
import geonamescache
import sqlalchemy as sa
from sqlalchemy import event
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.plugins import move_catalog
from app.plugins.provider import VibeProvider
from app import lifecycle, models, schema, types
from app.data_store import assets as ds_assets
from app.data_store import monstore

_LOGGER = structlog.get_logger(__name__)

PROVIDERS: list[VibeProvider] = [ClimateProvider()]
PROVIDERS_BY_NAME: dict[str, VibeProvider] = {p.name: p for p in PROVIDERS}

DEFAULT_TRAINER_USERNAME = "Script Trainer"
DUMP_ROOT = pathlib.Path(__file__).parent.joinpath("generated")


class Stage(enum.StrEnum):
    PREVIEW = "preview"
    ADOPT = "adopt"


def _identity_to_model(identity: schema.Identity, vibemon_id: Any) -> models.Identity:
    """Build a fresh ``models.Identity`` row from a schema identity."""
    return models.Identity(
        vibemon_id=vibemon_id,
        name=identity.name,
        visual_notes=identity.visual_notes,
        provider_visual_notes=identity.provider_visual_notes,
        elements=[e.value for e in identity.elements],
        base_hp=identity.base_hp,
        base_attack=identity.base_attack,
        base_defense=identity.base_defense,
        base_sp_attack=identity.base_sp_attack,
        base_sp_defense=identity.base_sp_defense,
        base_speed=identity.base_speed,
        evo_seed=int(identity.evo_seed),
        is_radiant=identity.is_radiant,
        generation=identity.generation,
        generated_at=identity.generated_at,
    )


def _vibemon_moves(
    vibemon: schema.Vibemon,
    cache: dict[str, models.Move],
    *,
    learned_at_ts: dt.datetime,
) -> list[models.VibemonMove]:
    """Build ``VibemonMove`` join rows for a vibemon's active moves (slots 0..3)."""
    rows: list[models.VibemonMove] = []
    for slot, mv in enumerate(vibemon.moves):
        move_row, _, _ = move_catalog.upsert_move(mv, cache)
        rows.append(
            models.VibemonMove(
                move=move_row,
                learned_at_level=1,
                learned_at_ts=learned_at_ts,
                active_slot=slot,
            )
        )
    return rows


async def log_vibemon(event: str, vibemon: schema.Vibemon, **extra: Any) -> None:
    await _LOGGER.ainfo(
        event,
        id=str(vibemon.id),
        name=vibemon.name,
        type=tuple(map(str, vibemon.elements)),
        tier=vibemon.identity.tier,
        role=vibemon.identity.battle_role.name,
        moves=[f"{m.name} [{m.type}]" for m in vibemon.moves],
        lifecycle=vibemon.lifecycle.value,
        trainer_id=str(vibemon.trainer_id) if vibemon.trainer_id else None,
        **extra,
    )


@asynccontextmanager
async def database_session(db_path: str) -> AsyncIterator[AsyncSession]:
    """Spin up an async SQLite db, create tables, yield a session."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        # SQLite disables FK enforcement by default; force it on for every connection.
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with async_session() as sess:
            yield sess
    finally:
        await engine.dispose()


def get_random_city() -> tuple[str, str, float, float]:
    """Pick a random city. Returns (name, country, lat, lng)."""
    cache = geonamescache.GeonamesCache()
    city = random.choice(list(cache.get_cities().values()))
    country = cache.get_countries()[city["countrycode"]]["name"]
    return city["name"], country, city["latitude"], city["longitude"]


async def generate_vibemon_in_world(
    *,
    stage: Stage,
    trainer_id: types.TrainerIdT | None = None,
    **vibemon_options: Any,
) -> tuple[str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]:
    """Generate a Vibemon in a random city.

    Returns ``(country, seed, snapshot, vibemon)``. The Vibemon's lifecycle
    advances as far as the requested ``stage`` allows.
    """
    _, country, lat, lng = get_random_city()

    seed = schema.BirthSeed(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(lat, lng),
        providers=PROVIDERS,
    )

    snapshot = await seed.fetch_snapshot()
    affinities = await snapshot.regenerate(seed.providers, seed)
    vibemon = schema.Vibemon.birth(*affinities, birth_seed=seed, **vibemon_options)

    await lifecycle.christen(vibemon)

    if stage is Stage.ADOPT:
        if trainer_id is None:
            raise ValueError("adopt stage requires a trainer_id")
        await lifecycle.adopt(vibemon, trainer_id)

    return country, seed, snapshot, vibemon


async def stream_vibemon_in_world(
    count: int,
    *,
    stagger: float,
    stage: Stage,
    trainer_id: types.TrainerIdT | None,
    **vibemon_options: Any,
) -> AsyncIterator[tuple[str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]]:
    """Yield concurrently-born vibemon in completion order. Per-task stagger avoids
    a thundering herd on upstream providers."""

    async def _delayed(delay: float):
        await asyncio.sleep(delay)

        try:
            return await generate_vibemon_in_world(
                stage=stage, trainer_id=trainer_id, **vibemon_options
            )
        except Exception as e:
            await _LOGGER.awarning("Birth failed, skipping", error=repr(e))

    tasks = [asyncio.create_task(_delayed(i * stagger)) for i in range(count)]

    try:
        async for coro in asyncio.as_completed(tasks):
            if (result := await coro) is not None:
                yield result
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()


async def _load_moves_cache(sess: AsyncSession) -> dict[str, models.Move]:
    return await move_catalog.load_move_cache(sess)


async def _ensure_trainer(sess: AsyncSession, username: str) -> models.Trainer:
    """Find or create a stable script trainer."""
    existing = (
        await sess.execute(
            sa.select(models.Trainer).where(models.Trainer.username == username)
        )
    ).scalar_one_or_none()

    if existing is not None:
        return existing

    trainer = models.Trainer(username=username)
    sess.add(trainer)
    await sess.commit()
    await sess.refresh(trainer)
    return trainer


async def birth_many_vibemon(
    sess: AsyncSession,
    *,
    count: int,
    stagger: float,
    stage: Stage,
    trainer: models.Trainer | None,
    core_identity: str | None,
    seed_provider_moves: bool,
) -> int:
    """Birth `count` fresh vibemon, persisting each as it arrives."""
    moves_cache = await _load_moves_cache(sess)
    if seed_provider_moves:
        created, updated = await move_catalog.sync_provider_moves(
            sess, PROVIDERS, cache=moves_cache
        )
        if created or updated:
            await sess.commit()
        await _LOGGER.ainfo(
            "Synced provider move catalog", created=created, updated=updated
        )
    trainer_id = trainer.id if trainer is not None else None

    persisted_count = 0

    async for country, seed, snapshot, vibemon in stream_vibemon_in_world(
        count=count,
        stagger=stagger,
        stage=stage,
        trainer_id=trainer_id,
        core_identity=core_identity,
    ):
        snapshot_model = models.BirthSnapshot(
            provider_payloads=dict(snapshot.provider_payloads),
            birth_seed=models.BirthSeed(
                timestamp=seed.timestamp,
                geo_coords=list(seed.geo_coords),
            ),
        )

        now = dt.datetime.now(tz=dt.timezone.utc)
        vibemon_model = models.Vibemon(
            id=vibemon.id,
            nickname=vibemon.nickname,
            xp=vibemon.xp,
            level=vibemon.level,
            evo_stage=int(vibemon.evo_stage),
            lifecycle=vibemon.lifecycle.value,
            team_slot=vibemon.team_slot,
            trainer_id=vibemon.trainer_id,
            birth_snapshot=snapshot_model,
        )
        vibemon_model.identity = _identity_to_model(vibemon.identity, vibemon.id)
        vibemon_model.moves = _vibemon_moves(vibemon, moves_cache, learned_at_ts=now)

        sess.add(vibemon_model)

        if vibemon.aesthetic is not None and vibemon.aesthetic.assets:
            await ds_assets.upsert(sess, vibemon.id, vibemon.aesthetic.assets.values())

        await sess.commit()

        persisted_count += 1

        await dump_vibemon_assets(vibemon)
        await log_vibemon("Persisted Vibemon", vibemon, country=country)

    return persisted_count


async def rebirth_all_vibemon(sess: AsyncSession, *, seed_provider_moves: bool) -> int:
    """Re-run merge/balance on every persisted Vibemon, in place. No network."""
    moves_cache = await _load_moves_cache(sess)
    if seed_provider_moves:
        created, updated = await move_catalog.sync_provider_moves(
            sess, PROVIDERS, cache=moves_cache
        )
        if created or updated:
            await sess.commit()
        await _LOGGER.ainfo(
            "Synced provider move catalog", created=created, updated=updated
        )

    result = await sess.execute(
        sa.select(models.Vibemon).options(
            selectinload(models.Vibemon.identity),
            selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
            selectinload(models.Vibemon.birth_snapshot).selectinload(
                models.BirthSnapshot.birth_seed
            ),
            selectinload(models.Vibemon.assets),
        )
    )

    persisted_count = 0

    for vibemon_model in result.scalars():
        snapshot_model = vibemon_model.birth_snapshot

        if snapshot_model is None or snapshot_model.birth_seed is None:
            await _LOGGER.awarning(
                "Skipping vibemon — no birth_snapshot/birth_seed",
                id=str(vibemon_model.id),
            )
            continue

        seed_model = snapshot_model.birth_seed

        try:
            providers = [
                PROVIDERS_BY_NAME[name] for name in snapshot_model.provider_payloads
            ]
        except KeyError as e:
            await _LOGGER.awarning(
                "Skipping vibemon — unknown provider", missing=str(e)
            )
            continue

        seed = schema.BirthSeed(
            timestamp=seed_model.timestamp,
            geo_coords=tuple(seed_model.geo_coords),
            providers=providers,
        )

        snapshot = schema.BirthSnapshot(
            provider_payloads=snapshot_model.provider_payloads
        )

        if not (affinities := await snapshot.regenerate(providers, seed)):
            continue

        reborn = schema.Vibemon.rebirth(
            *affinities,
            id=vibemon_model.id,
            name=vibemon_model.identity.name,
            birth_seed=seed,
            core_identity=vibemon_model.identity.visual_notes,
            nickname=vibemon_model.nickname,
            level=vibemon_model.level,
            xp=vibemon_model.xp,
            evo_stage=types.EvolutionStageT(vibemon_model.evo_stage),
        )

        # Bump generation; replace identity fields in place (do NOT swap the
        # relationship — that would trigger delete-orphan on the existing row).
        reborn.identity = reborn.identity.model_copy(
            update={
                "generation": vibemon_model.identity.generation + 1,
                "generated_at": dt.datetime.now(tz=dt.timezone.utc),
            }
        )

        identity_row = vibemon_model.identity
        identity_row.name = reborn.identity.name
        identity_row.visual_notes = reborn.identity.visual_notes
        identity_row.provider_visual_notes = reborn.identity.provider_visual_notes
        identity_row.elements = [e.value for e in reborn.identity.elements]
        identity_row.base_hp = reborn.identity.base_hp
        identity_row.base_attack = reborn.identity.base_attack
        identity_row.base_defense = reborn.identity.base_defense
        identity_row.base_sp_attack = reborn.identity.base_sp_attack
        identity_row.base_sp_defense = reborn.identity.base_sp_defense
        identity_row.base_speed = reborn.identity.base_speed
        identity_row.evo_seed = int(reborn.identity.evo_seed)
        identity_row.is_radiant = reborn.identity.is_radiant
        identity_row.generation = reborn.identity.generation
        identity_row.generated_at = reborn.identity.generated_at

        vibemon_model.evo_stage = int(reborn.evo_stage)
        vibemon_model.lifecycle = reborn.lifecycle.value
        vibemon_model.moves = _vibemon_moves(
            reborn,
            moves_cache,
            learned_at_ts=dt.datetime.now(tz=dt.timezone.utc),
        )

        # Rebirth has no network; previous asset blobs are now stale candidates.
        await ds_assets.delete_for_vibemon(sess, vibemon_model.id)

        await sess.commit()

        persisted_count += 1

        await log_vibemon("Reborn Vibemon", reborn)

    return persisted_count


async def dump_vibemon_assets(vibemon: schema.Vibemon) -> None:
    """Dump a Vibemon's assets to disk under ``.scripts/generated/<uuid>/``.

    Writes a ``name.txt`` summary and any populated asset blobs. Subdirectories
    follow ``AssetKind.value`` (e.g. ``sprite/reference.png``).
    """
    if vibemon.aesthetic is None:
        raise RuntimeError(f"Cannot dump Vibemon {vibemon.id}: aesthetic is missing")

    target = DUMP_ROOT / str(vibemon.id)
    target.mkdir(parents=True, exist_ok=True)

    (target / "name.txt").write_text(
        f"id: {vibemon.id}\n"
        f"name: {vibemon.name}\n"
        f"lifecycle: {vibemon.lifecycle.value}\n",
        encoding="utf-8",
    )

    for kind, ref in vibemon.aesthetic.assets.items():
        path = target / kind.value
        path.parent.mkdir(parents=True, exist_ok=True)
        data = await monstore.get(ref.key)
        path.write_bytes(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--count", type=int, default=1, help="Ignored when --rebirth is set."
    )
    parser.add_argument("--core-identity", type=str, default=None)
    parser.add_argument(
        "--stage",
        type=Stage,
        choices=list(Stage),
        default=Stage.PREVIEW,
        help="preview: christen only. adopt: christen then assign trainer + manifest.",
    )
    parser.add_argument(
        "--trainer-username", type=str, default=DEFAULT_TRAINER_USERNAME
    )
    parser.add_argument("--stagger", type=float, default=2.0)
    parser.add_argument(
        "--db-path",
        type=str,
        default=pathlib.Path(__file__).parent.joinpath("vibemon.db").as_posix(),
    )
    parser.add_argument(
        "--rebirth",
        action="store_true",
        help="Re-run merge/balance on all persisted vibemon in place. No network.",
    )
    parser.add_argument(
        "--seed-provider-moves",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Upsert provider move catalogs into the move table before generation/rebirth.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO)
    )

    await _LOGGER.ainfo("Starting", stage=args.stage.value, rebirth=args.rebirth)

    async with database_session(db_path=args.db_path) as sess:
        if args.rebirth:
            count = await rebirth_all_vibemon(
                sess, seed_provider_moves=args.seed_provider_moves
            )
        else:
            trainer = (
                await _ensure_trainer(sess, args.trainer_username)
                if args.stage is Stage.ADOPT
                else None
            )
            count = await birth_many_vibemon(
                sess,
                count=args.count,
                stagger=args.stagger,
                stage=args.stage,
                trainer=trainer,
                core_identity=args.core_identity,
                seed_provider_moves=args.seed_provider_moves,
            )

        await _LOGGER.ainfo("Complete", n_mons=count)


if __name__ == "__main__":
    asyncio.run(main())
