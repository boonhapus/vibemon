# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "geonamescache", "structlog", "rich"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///

"""CLI: fetch weather twice, build two Vibemon, print them with Rich."""

import asyncio
import datetime as dt
import pathlib
import random

from rich import console, table
import geonamescache
import structlog

from app.plugins.climate.provider import ClimateProvider
from app.settings import settings
from app import schema

_LOGGER = structlog.get_logger(__name__)
rich_console = console.Console()


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


async def main() -> None:
    """Entrypoint."""
    settings.headless = True

    rows = await asyncio.gather(*(generate_vibemon_in_world() for _ in range(10)))

    rich_console.print()
    rich_console.print(_build_summary_table(rows))
    rich_console.print()


if __name__ == "__main__":
    asyncio.run(main())
