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
import argparse
import asyncio
import datetime as dt
import logging
import pathlib
import random

from PIL.Image import Image
import geonamescache
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.settings import settings
from app import models, schema

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

_LOGGER = structlog.get_logger(__name__)


def schema_to_models(
    vibemon: schema.Vibemon,
    *,
    birth_seed: schema.BirthSeed | None = None,
    birth_snapshot: schema.BirthSnapshot | None = None,
    moves_cache: dict[str, models.Move] | None = None,
) -> models.Vibemon:
    """Convert Pydantic schema objects to SQLAlchemy models.

    Builds a relationship graph rooted at the returned ``models.Vibemon``;
    a single ``session.add(...)`` cascades through ``affinity``, ``identity``,
    ``moves``, ``birth_seed`` (with nested ``birth_snapshots``), and
    ``birth_affinities`` via the
    ``back_populates`` wiring.

    Moves are de-duplicated by name (``models.Move.name`` is ``unique=True``).
    Three flavours of overlap can collide on that constraint:

    1. *Within a Vibemon* — the merged ``affinity`` re-uses ``Move`` instances
       sampled out of ``birth_affinities``.
    2. *Across a batch* — two Vibemons may independently draw a move with the
       same name (e.g. both ghost-typed climate Vibemon receiving "Neon Squall").
    3. *Across runs* — the SQLite file persists, so a name created last run
       is still in ``move``.

    Pass a shared ``moves_cache`` across calls to handle (2); pre-populate it
    from the DB to handle (3). When omitted, a fresh per-call cache covers (1)
    only.
    """
    moves_by_name = moves_cache if moves_cache is not None else {}

    def _move(move: schema.Move) -> models.Move:
        if (existing := moves_by_name.get(move.name)) is not None:
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
        moves_by_name[move.name] = m
        return m

    def _identity(identity: schema.Identity) -> models.Identity:
        return models.Identity(
            name=identity.name,
            visual_notes=identity.visual_notes,
            elements=[e.value for e in identity.elements],
            base_hp=identity.base_hp,
            base_attack=identity.base_attack,
            base_defense=identity.base_defense,
            base_sp_attack=identity.base_sp_attack,
            base_sp_defense=identity.base_sp_defense,
            base_speed=identity.base_speed,
            evo_seed=identity.evo_seed,
            evo_stage=identity.evo_stage.name,
            is_radiant=identity.is_radiant,
        )

    def _affinity(affinity: schema.Affinity) -> models.Affinity:
        return models.Affinity(
            identity=_identity(affinity.identity),
            visual_notes=affinity.visual_notes,
            intensity=affinity.intensity,
            provider_id=affinity.provider_id,
            moves=[_move(m) for m in affinity.moves],
        )

    def _birth_seed(seed: schema.BirthSeed) -> models.BirthSeed:
        return models.BirthSeed(
            timestamp=int(seed.timestamp.timestamp()),
            geo_coords=list(seed.geo_coords),
            provider_names=[provider.name for provider in seed.providers],
        )

    def _birth_snapshot(snapshot: schema.BirthSnapshot) -> models.BirthSnapshot:
        return models.BirthSnapshot(
            provider_payloads={
                provider_id: payload
                for provider_id, payload in snapshot.provider_payloads.items()
            }
        )

    model_vibemon = models.Vibemon(
        nickname=vibemon.nickname,
        affinity=_affinity(vibemon.affinity),
        level=vibemon.level,
        birth_affinities=[_affinity(a) for a in vibemon.birth_affinities],
    )

    model_birth_seed: models.BirthSeed | None = None

    if birth_seed is not None:
        model_birth_seed = _birth_seed(birth_seed)

    if birth_snapshot is not None:
        if model_birth_seed is None:
            raise ValueError("birth_snapshot requires a birth_seed.")
        model_birth_seed.birth_snapshots.append(_birth_snapshot(birth_snapshot))

    if model_birth_seed is not None:
        model_vibemon.birth_seed = model_birth_seed

    return model_vibemon


@asynccontextmanager
async def database_session(db_path: str | None = None) -> AsyncIterator[AsyncSession]:
    db_path = db_path or str(pathlib.Path(__file__).parent / "vibemon.db")
    """Spin up an async SQLite db, create tables, yield a session.

    The engine is disposed on exit so the script doesn't leak the aiosqlite
    pool — important when this is invoked from longer-lived hosts (e.g. a
    notebook or a future service) rather than a one-shot CLI run.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

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


def get_random_city() -> geonamescache.City:
    """Fetch a random city."""
    cache = geonamescache.GeonamesCache()

    city = random.choice([c for c in cache.get_cities().values()])
    country = next(
        c for iso, c in cache.get_countries().items() if iso == city["countrycode"]
    )

    # Add the Country.name
    city["country"] = country["name"]

    return city


async def generate_vibemon_in_world(
    **vibemon_options,
) -> tuple[str, str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]:
    """Generate a Vibemon in some random city."""
    city = get_random_city()

    seed = schema.BirthSeed(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(city["latitude"], city["longitude"]),
        providers=[ClimateProvider()],
    )

    snapshot = await seed.fetch_snapshot()
    affinities = await snapshot.regenerate(seed.providers, seed)
    vibemon = await schema.Vibemon.birth(*affinities, **vibemon_options)

    if not settings.headless:
        assert vibemon.aesthetic.battle_cry is not None, ""
        assert vibemon.aesthetic.sprites is not None, ""

        directory = pathlib.Path(__file__).parent / "generated" / vibemon.name.lower()
        directory.mkdir(parents=True, exist_ok=True)

        directory.joinpath("battle_cry.mp3").write_bytes(vibemon.aesthetic.battle_cry)

        for key, sprite in vibemon.aesthetic.sprites.items():
            assert isinstance(sprite, Image), ""
            sprite.save(directory.joinpath(f"{key}.png"))

    return (city["name"], city["country"], seed, snapshot, vibemon)


async def stream_vibemon_in_world(
    count: int,
    *,
    stagger: float = 2,
    **vibemon_options,
) -> AsyncIterator[tuple[str, str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]]:
    """Generate Vibemon concurrently, yielding each one as soon as it's ready.

    Tasks are launched with a per-task stagger so we don't hit upstream providers
    in a thundering herd; results are yielded in completion order (not start
    order) so the consumer can begin persisting immediately while the rest are
    still being born.
    """

    async def _delayed(
        delay: float,
    ) -> tuple[str, str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon] | None:
        await asyncio.sleep(delay)
        try:
            return await generate_vibemon_in_world(**vibemon_options)
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


def parse_args() -> argparse.Namespace:
    """Parse CLI options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=150)
    parser.add_argument("--core-identity", type=str, default=None)
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--stagger", type=float, default=2.0)
    parser.add_argument("--db-path", type=str, default=pathlib.Path(__file__).parent.joinpath("vibemon.db").as_posix())
    return parser.parse_args()


async def main() -> None:
    """Entrypoint."""
    args = parse_args()

    settings.headless = args.headless

    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    await _LOGGER.ainfo("Starting", headless=settings.headless)

    rows: list[tuple[str, str, schema.BirthSeed, schema.BirthSnapshot, schema.Vibemon]] = []

    async with database_session(db_path=args.db_path) as sess:
        existing_moves = (await sess.execute(sa.select(models.Move))).scalars().all()
        moves_cache: dict[str, models.Move] = {m.name: m for m in existing_moves}

        async for item in stream_vibemon_in_world(count=args.count, stagger=args.stagger, core_identity=args.core_identity):
            _, country, seed, snapshot, vibemon = item
            sess.add(
                schema_to_models(
                    vibemon,
                    birth_seed=seed,
                    birth_snapshot=snapshot,
                    moves_cache=moves_cache,
                )
            )
            await sess.commit()
            await _LOGGER.ainfo(
                "Persisted Vibemon",
                name=vibemon.name,
                type=tuple(map(str, vibemon.elements)),
                country=country,
                tier=vibemon.affinity.identity.tier,
                role=vibemon.affinity.identity.battle_role.name,
                moves=[f"{m.name} [{m.type}]" for m in vibemon.affinity.moves],
            )
            rows.append(item)


if __name__ == "__main__":
    asyncio.run(main())
