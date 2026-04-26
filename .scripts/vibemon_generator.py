# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "pyperclip", "python-dotenv", "rembg[cpu]", "rich"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../backend" , editable = true }
# ///

"""CLI: fetch weather twice, build two Vibemon, print them with Rich."""

import asyncio
import datetime as dt
import os
import pathlib
import sys

from rich import console
import dotenv

from app.plugins.climate.base import ClimateProvider
from app import schema

rich_console = console.Console()


async def main() -> None:
    """Entrypoint."""
    dotenv.load_dotenv()

    if not os.environ.get("WEATHER_API_KEY"):
        rich_console.print("[red]Set WEATHER_API_KEY (WeatherAPI.com).[/red]")
        sys.exit(1)

    # AMAZON RAINFOREST
    # lat = float(os.environ.get("VIBEMON_LAT", "-4.0000"))
    # lon = float(os.environ.get("VIBEMON_LON", "-63.0000"))

    # LAS VEGAS
    # lat = float(os.environ.get("VIBEMON_LAT", "36.1159"))
    # lon = float(os.environ.get("VIBEMON_LON", "-115.1719"))

    # Shibuya Station
    lat = float(os.environ.get("VIBEMON_LAT", "35.658034"))
    lon = float(os.environ.get("VIBEMON_LON", "139.701636"))

    rich_console.print(f"[dim]Coords[/] {lat:.4f}, {lon:.4f}\n")

    ctx = schema.BirthContext(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(lat, lon),
        providers=[ClimateProvider()],
    )

    affinities = await ctx.regenerate()

    vibemon = await schema.Vibemon.birth(*affinities, core_identity="Has a sunny disposition")

    for key, sprite in vibemon.aesthetic.sprites.items():
        sprite.save(pathlib.Path(__file__).parent / "generated" / f"{vibemon.name.lower()}_{key}.png")

    rich_console.print(vibemon)


if __name__ == "__main__":
    asyncio.run(main())
