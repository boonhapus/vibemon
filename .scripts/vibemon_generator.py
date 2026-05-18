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
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload, sessionmaker
from sqlalchemy import event
import geonamescache
import sqlalchemy as sa
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.plugins import move_catalog
from app.plugins.provider import VibeProvider
from app.services.vibemon_service import VibemonService
from app import models, schema, types
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


async def log_vibemon(event: str, public: schema.PublicVibemon, **extra: Any) -> None:
    await _LOGGER.ainfo(
        event,
        id=str(public.id),
        name=public.name,
        type=tuple(map(str, public.identity.elements)),
        moves=[f"{m.name} [{m.type}]" for m in public.moves],
        lifecycle=public.lifecycle.value,
        disposition=public.disposition.value if public.disposition else None,
        trainer_id=str(public.trainer_id) if public.trainer_id else None,
        **extra,
    )


@asynccontextmanager
async def database_session(db_path: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as sess:
            yield sess
    finally:
        await engine.dispose()


def get_random_city() -> tuple[str, str, float, float]:
    cache = geonamescache.GeonamesCache()
    city = random.choice(list(cache.get_cities().values()))
    country = cache.get_countries()[city["countrycode"]]["name"]
    return city["name"], country, city["latitude"], city["longitude"]


async def _ensure_trainer(sess: AsyncSession, username: str) -> models.Trainer:
    existing = (
        await sess.execute(sa.select(models.Trainer).where(models.Trainer.username == username))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    trainer = models.Trainer(username=username)
    sess.add(trainer)
    await sess.commit()
    await sess.refresh(trainer)
    return trainer


def _random_seed() -> tuple[str, schema.BirthSeed]:
    _, country, lat, lng = get_random_city()
    seed = schema.BirthSeed(
        timestamp=dt.datetime.now(tz=dt.UTC),
        geo_coords=(lat, lng),
        providers=PROVIDERS,
    )
    return country, seed


async def generate_via_service(
    sess: AsyncSession,
    service: VibemonService,
    *,
    trainer_id: types.TrainerIdT,
    stage: Stage,
    core_identity: str | None,
) -> tuple[str, schema.PublicVibemon]:
    country, seed = _random_seed()
    public = await service.generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=seed,
        core_identity=core_identity,
        bypass_credits=True,
    )
    if stage is Stage.ADOPT:
        public = await service.adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=public.id)
    return country, public


async def birth_many_vibemon(
    sess: AsyncSession,
    *,
    count: int,
    stage: Stage,
    trainer: models.Trainer,
    core_identity: str | None,
    seed_provider_moves: bool,
) -> int:
    if seed_provider_moves:
        cache = await move_catalog.load_move_cache(sess)
        created, updated = await move_catalog.sync_provider_moves(sess, PROVIDERS, cache=cache)
        if created or updated:
            await sess.commit()
        await _LOGGER.ainfo("Synced provider move catalog", created=created, updated=updated)

    service = VibemonService()
    persisted = 0
    for _ in range(count):
        try:
            country, public = await generate_via_service(
                sess,
                service,
                trainer_id=trainer.id,
                stage=stage,
                core_identity=core_identity,
            )
        except Exception as e:
            await sess.rollback()
            await _LOGGER.awarning("Birth failed, skipping", error=repr(e))
            continue

        await sess.commit()
        persisted += 1
        await dump_vibemon_assets(sess, public.id)
        await log_vibemon("Persisted Vibemon", public, country=country)

    return persisted


async def rebirth_all_vibemon(sess: AsyncSession, *, seed_provider_moves: bool) -> int:
    """Re-run merge/balance on every persisted Vibemon, in place. No network."""
    moves_cache = await move_catalog.load_move_cache(sess)
    if seed_provider_moves:
        created, updated = await move_catalog.sync_provider_moves(sess, PROVIDERS, cache=moves_cache)
        if created or updated:
            await sess.commit()
        await _LOGGER.ainfo("Synced provider move catalog", created=created, updated=updated)

    result = await sess.execute(
        sa.select(models.Vibemon).options(
            selectinload(models.Vibemon.identity),
            selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
            selectinload(models.Vibemon.birth_snapshot).selectinload(models.BirthSnapshot.birth_seed),
            selectinload(models.Vibemon.assets),
        )
    )

    persisted_count = 0

    for vibemon_model in result.scalars():
        snapshot_model = vibemon_model.birth_snapshot
        if snapshot_model is None or snapshot_model.birth_seed is None:
            await _LOGGER.awarning("Skipping vibemon — no birth_snapshot/birth_seed", id=str(vibemon_model.id))
            continue

        seed_model = snapshot_model.birth_seed
        try:
            providers = [PROVIDERS_BY_NAME[name] for name in snapshot_model.provider_payloads]
        except KeyError as e:
            await _LOGGER.awarning("Skipping vibemon — unknown provider", missing=str(e))
            continue

        seed = schema.BirthSeed(
            timestamp=seed_model.timestamp,
            geo_coords=tuple(seed_model.geo_coords),
            providers=providers,
        )
        snapshot = schema.BirthSnapshot(provider_payloads=snapshot_model.provider_payloads)

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

        reborn.identity = reborn.identity.model_copy(
            update={
                "generation": vibemon_model.identity.generation + 1,
                "generated_at": dt.datetime.now(tz=dt.UTC),
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

        learned_at = dt.datetime.now(tz=dt.UTC)
        new_moves: list[models.VibemonMove] = []
        for slot, mv in enumerate(reborn.moves):
            move_row, _, _ = move_catalog.upsert_move(mv, moves_cache)
            new_moves.append(
                models.VibemonMove(
                    move=move_row,
                    learned_at_level=1,
                    learned_at_ts=learned_at,
                    active_slot=slot,
                )
            )
        vibemon_model.moves = new_moves

        await ds_assets.delete_for_vibemon(sess, vibemon_model.id)
        await sess.commit()
        persisted_count += 1

        await _LOGGER.ainfo("Reborn Vibemon", id=str(vibemon_model.id), name=reborn.name)

    return persisted_count


async def dump_vibemon_assets(sess: AsyncSession, vibemon_id: uuid.UUID) -> None:
    """Dump persisted asset blobs to disk under ``.scripts/generated/<uuid>/``."""
    rows = (
        (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id)))
        .scalars()
        .all()
    )
    if not rows:
        return

    target = DUMP_ROOT / str(vibemon_id)
    target.mkdir(parents=True, exist_ok=True)

    for row in rows:
        path = target / row.kind
        path.parent.mkdir(parents=True, exist_ok=True)
        data = await monstore.get(row.object_key)
        path.write_bytes(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1, help="Ignored when --rebirth is set.")
    parser.add_argument("--core-identity", type=str, default=None)
    parser.add_argument(
        "--stage",
        type=Stage,
        choices=list(Stage),
        default=Stage.PREVIEW,
        help="preview: candidate review only. adopt: christen then adopt + manifest.",
    )
    parser.add_argument("--trainer-username", type=str, default=DEFAULT_TRAINER_USERNAME)
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

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    await _LOGGER.ainfo("Starting", stage=args.stage.value, rebirth=args.rebirth)

    async with database_session(db_path=args.db_path) as sess:
        if args.rebirth:
            count = await rebirth_all_vibemon(sess, seed_provider_moves=args.seed_provider_moves)
        else:
            trainer = await _ensure_trainer(sess, args.trainer_username)
            count = await birth_many_vibemon(
                sess,
                count=args.count,
                stage=args.stage,
                trainer=trainer,
                core_identity=args.core_identity,
                seed_provider_moves=args.seed_provider_moves,
            )

        await _LOGGER.ainfo("Complete", n_mons=count)


if __name__ == "__main__":
    asyncio.run(main())
