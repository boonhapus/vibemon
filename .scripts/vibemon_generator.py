# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "python-dotenv", "rich"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///

"""CLI: fetch weather twice, build two Vibemon, print them with Rich."""

from __future__ import annotations

import asyncio
import concurrent.futures
import datetime as dt
import os
import re
import secrets
import sys
from collections.abc import Coroutine
from typing import Any, TypeVar

import dotenv
from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table

from app import schema
from app.plugins.climate.base import ClimateProvider

console = Console()

_T = TypeVar("_T")


def run_coro(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run async code from sync context. Uses ``asyncio.run`` unless a loop is already running (e.g. Jupyter)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(coro)).result()


def birth_context(latitude: float, longitude: float) -> schema.BirthContext:
    return schema.BirthContext(
        seed=secrets.token_hex(4),
        timestamp=dt.datetime.now(dt.UTC),
        geo_coords=(latitude, longitude),
        weather_conditions=None,
        providers={},
    )


async def fetch_two_affinities(ctx: schema.BirthContext) -> tuple[schema.Affinity, schema.Affinity]:
    """One event loop for the whole client lifetime (avoids loop-closed on teardown)."""
    provider = ClimateProvider()
    try:
        first = await provider.generate(ctx)
        second = await provider.generate(ctx)
        return first, second
    finally:
        await provider.teardown()


def print_vibemon(mon: schema.Vibemon) -> None:
    # Rich defaults are tight against the panel border on Windows box drawing.
    stats = Table(
        "HP",
        "Atk",
        "Def",
        "SpA",
        "SpD",
        "Spe",
        "BST",
        box=box.SIMPLE,
        title="Stats (actual)",
        padding=(0, 2),
    )
    stats.add_row(
        str(mon.hp),
        str(mon.attack),
        str(mon.defense),
        str(mon.sp_attack),
        str(mon.sp_defense),
        str(mon.speed),
        str(mon.bst),
    )

    moves = Table("Move", "Type", "Category", "Power", box=box.SIMPLE, title="Moves")
    for m in mon.moves:
        moves.add_row(m.name, m.type.value, m.category.value, str(m.power))

    body = Group(
        f"[dim]{', '.join(t.value for t in mon.elements)}[/]",
        mon.description,
        stats,
        moves,
    )
    console.print(
        Panel.fit(
            body,
            title=f"[bold cyan]{mon.name}[/]",
            border_style="cyan",
            padding=(0, 2),
            safe_box=True,
        )
    )


def main() -> None:
    dotenv.load_dotenv()

    if not os.environ.get("WEATHER_API_KEY"):
        console.print("[red]Set WEATHER_API_KEY (WeatherAPI.com).[/red]")
        sys.exit(1)

    lat = float(os.environ.get("VIBEMON_LAT", "51.5074"))
    lon = float(os.environ.get("VIBEMON_LON", "-0.1278"))
    ctx = birth_context(lat, lon)

    console.print(f"[dim]Coords[/] {lat:.4f}, {lon:.4f}\n")

    affinity_a, affinity_b = run_coro(fetch_two_affinities(ctx))

    for tag, affinity in (("Birdmon", affinity_a), ("Goober", affinity_b)):
        vibemon = schema.Vibemon.from_affinities(affinity, name=tag, description="")
        print_vibemon(vibemon)
        console.print()
        console.print(vibemon.visual_dna.render())
        console.print()


if __name__ == "__main__":
    main()
