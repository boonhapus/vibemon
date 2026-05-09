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
import logging
import pathlib
import random

import geonamescache
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.plugins.provider import VibeProvider
from app import models, schema

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
import sqlalchemy as sa

_LOGGER = structlog.get_logger(__name__)

PROVIDERS: list[VibeProvider] = [ClimateProvider()]
PROVIDERS_BY_NAME: dict[str, VibeProvider] = {p.name: p for p in PROVIDERS}


def affinity_schema_to_model(
    affinity: schema.Affinity,
    moves_cache: dict[str, models.Move],
) -> models.Affinity:
    """Convert a schema.Affinity to models.Affinity, deduping moves by name via cache."""

    def _move(move: schema.Move) -> models.Move:
        if (existing := moves_cache.get(move.name)) is not None:
            return existing

        m = models.Move(
            name=move.name,
            flavor_text=move.flavor_text,
            type=move.type.value,
            category=move.category.value,
            power=move.power,
            accuracy=move.accuracy,
            pp=move.pp,
            priority=move.priority,
            effects=[group.model_dump(mode="json") for group in move.effects],
            level_requirement=move.level_requirement,
        )
        moves_cache[move.name] = m
        return m

    return models.Affinity(
        identity=models.Identity(
            name=affinity.identity.name,
            visual_notes=affinity.identity.visual_notes,
            elements=[e.value for e in affinity.identity.elements],
            base_hp=affinity.identity.base_hp,
            base_attack=affinity.identity.base_attack,
            base_defense=affinity.identity.base_defense,
            base_sp_attack=affinity.identity.base_sp_attack,
            base_sp_defense=affinity.identity.base_sp_defense,
            base_speed=affinity.identity.base_speed,
            evo_seed=affinity.identity.evo_seed,
            evo_stage=affinity.identity.evo_stage.name,
            is_radiant=affinity.identity.is_radiant,
        ),
        visual_notes=affinity.visual_notes,
        intensity=affinity.intensity,
        provider_id=affinity.provider_id,
        moves=[_move(m) for m in affinity.moves],
    )


async def log_vibemon(event: str, vibemon: schema.Vibemon, **extra: Any) -> None:
    await _LOGGER.ainfo(
        event,
        name=vibemon.name,
        type=tuple(map(str, vibemon.elements)),
        tier=vibemon.affinity.identity.tier,
        role=vibemon.affinity.identity.battle_role.name,
        moves=[f"{m.name} [{m.type}]" for m in vibemon.affinity.moves],
        **extra,
    )


@asynccontextmanager
async def database_session(db_path: str) -> AsyncIterator[AsyncSession]:
    """Spin up an async SQLite db, create tables, yield a session."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
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


def write_aesthetic_to_disk(vibemon: schema.Vibemon) -> None:
    aesthetic = vibemon.aesthetic
    assert aesthetic.battle_cry is not None and aesthetic.sprites is not None

    directory = pathlib.Path(__file__).parent / "generated" / vibemon.name.lower()
    directory.mkdir(parents=True, exist_ok=True)
    directory.joinpath("battle_cry.mp3").write_bytes(aesthetic.battle_cry)
    for key, sprite in aesthetic.sprites.items():
        sprite.save(directory.joinpath(f"{key}.png"))


async def generate_vibemon_in_world(
    *,
    headless: bool = False,
    **vibemon_options: Any,
) -> tuple[str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]:
    """Generate a Vibemon in a random city. Returns (country, seed, snapshot, vibemon)."""
    _, country, lat, lng = get_random_city()

    seed = schema.BirthSeed(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(lat, lng),
        providers=PROVIDERS,
    )

    snapshot = await seed.fetch_snapshot()
    affinities = await snapshot.regenerate(seed.providers, seed)
    vibemon = schema.Vibemon.birth(*affinities, birth_seed=seed, **vibemon_options)
    await vibemon.christen()

    if not headless:
        await vibemon.render_aesthetic()
        write_aesthetic_to_disk(vibemon)

    return country, seed, snapshot, vibemon


async def stream_vibemon_in_world(
    count: int,
    *,
    stagger: float,
    headless: bool,
    **vibemon_options: Any,
) -> AsyncIterator[tuple[str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]]:
    """Yield concurrently-born vibemon in completion order. Per-task stagger avoids
    a thundering herd on upstream providers."""

    async def _delayed(delay: float):
        await asyncio.sleep(delay)
        try:
            return await generate_vibemon_in_world(headless=headless, **vibemon_options)
        except Exception as e:
            await _LOGGER.awarning("Birth failed, skipping", error=repr(e))
            return None

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
    return {m.name: m for m in (await sess.execute(sa.select(models.Move))).scalars()}


async def birth_many_vibemon(
    sess: AsyncSession,
    *,
    count: int,
    stagger: float,
    headless: bool,
    core_identity: str | None,
) -> None:
    """Birth `count` fresh vibemon, persisting each as it arrives."""
    moves_cache = await _load_moves_cache(sess)

    async for country, seed, snapshot, vibemon in stream_vibemon_in_world(
        count=count, stagger=stagger, headless=headless, core_identity=core_identity
    ):
        sess.add(models.Vibemon(
            nickname=vibemon.nickname,
            level=vibemon.level,
            affinity=affinity_schema_to_model(vibemon.affinity, moves_cache),
            birth_affinities=[
                affinity_schema_to_model(a, moves_cache) for a in vibemon.birth_affinities
            ],
            birth_seed=models.BirthSeed(
                timestamp=seed.timestamp,
                geo_coords=list(seed.geo_coords),
                provider_names=[p.name for p in seed.providers],
                birth_snapshots=[
                    models.BirthSnapshot(provider_payloads=dict(snapshot.provider_payloads))
                ],
            ),
        ))
        await sess.commit()
        await log_vibemon("Persisted Vibemon", vibemon, country=country)


async def rebirth_all_vibemon(sess: AsyncSession) -> int:
    """Re-run merge/balance on every persisted Vibemon, in place. No network."""
    moves_cache = await _load_moves_cache(sess)

    result = await sess.execute(
        sa.select(models.Vibemon).options(
            selectinload(models.Vibemon.affinity).selectinload(models.Affinity.identity),
            selectinload(models.Vibemon.affinity).selectinload(models.Affinity.moves),
            selectinload(models.Vibemon.birth_seed).selectinload(models.BirthSeed.birth_snapshots),
            selectinload(models.Vibemon.birth_affinities).selectinload(models.Affinity.identity),
            selectinload(models.Vibemon.birth_affinities).selectinload(models.Affinity.moves),
        )
    )

    reborn_count = 0
    for vibemon_model in result.scalars():
        seed_model = vibemon_model.birth_seed
        if seed_model is None or not seed_model.birth_snapshots:
            await _LOGGER.awarning("Skipping vibemon — no birth_seed/snapshot", id=str(vibemon_model.id))
            continue

        try:
            providers = [PROVIDERS_BY_NAME[name] for name in seed_model.provider_names]
        except KeyError as e:
            await _LOGGER.awarning("Skipping vibemon — unknown provider", missing=str(e))
            continue

        seed = schema.BirthSeed(
            timestamp=seed_model.timestamp,
            geo_coords=tuple(seed_model.geo_coords),
            providers=providers,
        )
        snapshot = schema.BirthSnapshot(
            provider_payloads=seed_model.birth_snapshots[0].provider_payloads
        )

        affinities = await snapshot.regenerate(providers, seed)
        if not affinities:
            continue

        reborn = schema.Vibemon.rebirth(
            *affinities,
            name=vibemon_model.affinity.identity.name,
            birth_seed=seed,
            core_identity=vibemon_model.affinity.identity.visual_notes,
            nickname=vibemon_model.nickname,
            level=vibemon_model.level,
        )

        # Cascade-deletes the old affinity + identity (single_parent delete-orphan).
        vibemon_model.affinity = affinity_schema_to_model(reborn.affinity, moves_cache)
        vibemon_model.birth_affinities = [
            affinity_schema_to_model(a, moves_cache) for a in reborn.birth_affinities
        ]

        await sess.commit()
        reborn_count += 1
        await log_vibemon("Reborn Vibemon", reborn)

    return reborn_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=150, help="Ignored when --rebirth is set.")
    parser.add_argument("--core-identity", type=str, default=None)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--stagger", type=float, default=2.0)
    parser.add_argument("--db-path", type=str, default=pathlib.Path(__file__).parent.joinpath("vibemon.db").as_posix())
    parser.add_argument("--rebirth", action="store_true",
        help="Re-run merge/balance on all persisted vibemon in place. No network.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))
    await _LOGGER.ainfo("Starting", headless=args.headless, rebirth=args.rebirth)

    async with database_session(db_path=args.db_path) as sess:
        if args.rebirth:
            count = await rebirth_all_vibemon(sess)
            await _LOGGER.ainfo("Rebirth complete", reborn=count)
        else:
            await birth_many_vibemon(
                sess,
                count=args.count,
                stagger=args.stagger,
                headless=args.headless,
                core_identity=args.core_identity,
            )


if __name__ == "__main__":
    asyncio.run(main())
