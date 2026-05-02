# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "vibemon-backend",
#   "geonamescache",
#   "rich",
#   "sqlalchemy[asyncio]",
#   "aiosqlite",
# ]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio
import datetime as dt
import logging
import pathlib
import random
import uuid

from rich import console, live, table
import geonamescache
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.settings import settings
from app import models, schema

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa


_LOGGER = structlog.get_logger(__name__)
rich_console = console.Console()


def schema_to_models(
    vibemon: schema.Vibemon,
    *,
    moves_cache: dict[str, models.Move] | None = None,
) -> models.Vibemon:
    """Convert Pydantic schema objects to SQLAlchemy models.

    Builds a relationship graph rooted at the returned ``models.Vibemon``;
    a single ``session.add(...)`` cascades through ``affinity``, ``identity``,
    ``moves``, and ``birth_affinities`` via the ``back_populates`` wiring.

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
            effect=move.effect.model_dump(mode="json") if move.effect is not None else None,
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
            is_mythic=identity.is_mythic,
        )

    def _affinity(affinity: schema.Affinity) -> models.Affinity:
        return models.Affinity(
            identity=_identity(affinity.identity),
            visual_notes=affinity.visual_notes,
            intensity=affinity.intensity,
            provider_id=affinity.provider_id,
            moves=[_move(m) for m in affinity.moves],
        )

    return models.Vibemon(
        nickname=vibemon.nickname,
        affinity=_affinity(vibemon.affinity),
        level=vibemon.level,
        birth_affinities=[_affinity(a) for a in vibemon.birth_affinities],
    )


@asynccontextmanager
async def database_session(db_path: str = "../.scripts/vibemon.db") -> AsyncIterator[AsyncSession]:
    """Spin up an async SQLite db, create tables, yield a session.

    The engine is disposed on exit so the script doesn't leak the aiosqlite
    pool — important when this is invoked from longer-lived hosts (e.g. a
    notebook or a future service) rather than a one-shot CLI run.
    """
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")

    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as sess:
            yield sess
    finally:
        await engine.dispose()


def get_random_city(population_ge: int = 1_000_000) -> geonamescache.City:
    """Fetch a random city."""
    cache = geonamescache.GeonamesCache()

    major_city = random.choice([c for c in cache.get_cities().values() if c["population"] >= population_ge])
    country    = next(c for iso, c in cache.get_countries().items() if iso == major_city["countrycode"])

    # Add the Country.name
    major_city["country"] = country["name"]

    return major_city


async def generate_vibemon_in_world() -> tuple[str, str, schema.BirthContext, schema.Vibemon]:
    """Generate a Vibemon in some random city."""
    major_city = get_random_city()

    ctx = schema.BirthContext(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(major_city["latitude"], major_city["longitude"]),
        providers=[ClimateProvider()],
    )

    affinities = await ctx.regenerate()
    vibemon = await schema.Vibemon.birth(*affinities, core_identity="Has a sunny disposition")

    if not settings.headless:
        directory = pathlib.Path(__file__).parent / "generated" / vibemon.name.lower()
        directory.mkdir(parents=True, exist_ok=True)

        directory.joinpath(f"battle_cry.mp3").write_bytes(vibemon.aesthetic.battle_cry)

        for key, sprite in vibemon.aesthetic.sprites.items():
            sprite.save(directory.joinpath(f"{key}.png"))

    return (major_city["name"], major_city["country"], ctx, vibemon)


def _build_summary_table(rows: list[tuple[str, str, schema.BirthContext, schema.Vibemon]]) -> table.Table:
    max_moves = max(len(v.affinity.moves) for _, _, _, v in rows) if rows else 0

    t = table.Table(
        title="Vibemon world sample",
        show_lines=True,
        expand=False,
    )
    t.add_column("City", style="cyan", no_wrap=True)
    t.add_column("Country", style="cyan", no_wrap=True)
    t.add_column("Name", style="magenta")
    t.add_column("Elements", style="yellow")
    t.add_column("HP", justify="right")
    t.add_column("Atk", justify="right")
    t.add_column("Def", justify="right")
    t.add_column("SpA", justify="right")
    t.add_column("SpD", justify="right")
    t.add_column("Spe", justify="right")
    t.add_column("BST", justify="right")

    for i in range(max_moves):
        t.add_column(f"Move {i + 1}", style="green")
        t.add_column(f"Type {i + 1}", style="dim")

    for city_name, country_name, _ctx, v in rows:
        ident = v.affinity.identity
        move_cells: list[str] = []
        for m in v.affinity.moves:
            move_cells.extend((m.name, m.type.value))
        for _ in range(max_moves - len(v.affinity.moves)):
            move_cells.extend(("", ""))

        t.add_row(
            city_name,
            country_name,
            v.name,
            " / ".join(e.value for e in ident.elements),
            str(ident.base_hp),
            str(ident.base_attack),
            str(ident.base_defense),
            str(ident.base_sp_attack),
            str(ident.base_sp_defense),
            str(ident.base_speed),
            str(ident.bst),
            *move_cells,
        )

    return t


async def stream_vibemon_in_world(
    count: int,
    *,
    stagger: float = 2.0,
) -> AsyncIterator[tuple[str, str, schema.BirthContext, schema.Vibemon]]:
    """Generate Vibemon concurrently, yielding each one as soon as it's ready.

    Tasks are launched with a per-task stagger so we don't hit upstream providers
    in a thundering herd; results are yielded in completion order (not start
    order) so the consumer can begin persisting immediately while the rest are
    still being born.
    """

    async def _delayed(delay: float) -> tuple[str, str, schema.BirthContext, schema.Vibemon]:
        await asyncio.sleep(delay)
        return await generate_vibemon_in_world()

    tasks = [asyncio.create_task(_delayed(i * stagger)) for i in range(count)]

    try:
        async for coro in asyncio.as_completed(tasks):
            yield await coro
    finally:
        for t in tasks:
            if not t.done():
                t.cancel()


async def main() -> None:
    """Entrypoint."""
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

    settings.headless = True

    rows: list[tuple[str, str, schema.BirthContext, schema.Vibemon]] = []

    async with database_session() as sess:
        existing_moves = (await sess.execute(sa.select(models.Move))).scalars().all()
        moves_cache: dict[str, models.Move] = {m.name: m for m in existing_moves}

        with live.Live(_build_summary_table(rows), console=rich_console, refresh_per_second=4) as table_view:
            async for item in stream_vibemon_in_world(count=489):
                city, country, _ctx, vibemon = item
                sess.add(schema_to_models(vibemon, moves_cache=moves_cache))
                await sess.commit()
                await _LOGGER.ainfo("Persisted Vibemon", name=vibemon.name, city=city, country=country)
                rows.append(item)
                table_view.update(_build_summary_table(rows))

    rich_console.print()


if __name__ == "__main__":
    asyncio.run(main())
