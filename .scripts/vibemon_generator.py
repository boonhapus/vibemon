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
import io
import os
import pathlib
import sys

from PIL import Image
from rich import console
import dotenv
import rembg

from app.genai.client import generate_vibemon_sprite
from app.plugins.climate.base import ClimateProvider
from app import schema
# from app.genai import utils

rich_console = console.Console()
REMBG_SESSION = rembg.new_session("birefnet-general")


async def main() -> None:
    dotenv.load_dotenv()

    if not os.environ.get("WEATHER_API_KEY"):
        rich_console.print("[red]Set WEATHER_API_KEY (WeatherAPI.com).[/red]")
        sys.exit(1)

    lat = float(os.environ.get("VIBEMON_LAT", "51.5074"))
    lon = float(os.environ.get("VIBEMON_LON", "-0.1278"))
    ctx = schema.BirthContext(
        timestamp=dt.datetime.now(tz=dt.timezone.utc),
        geo_coords=(lat, lon),
        providers={},
    )

    rich_console.print(f"[dim]Coords[/] {lat:.4f}, {lon:.4f}\n")

    provider = ClimateProvider()
    affinity = await provider.generate(ctx)

    vibemon = schema.Vibemon.merge_affinities(affinity, description="Has a sunny disposition")
    sprites = await generate_vibemon_sprite(vibemon=vibemon, bg_hex="#C47A7A")

    removed = rembg.remove(sprites, session=REMBG_SESSION)
    img_dir = pathlib.Path(__file__).parent
    
    # Write the sprite sheet
    with img_dir.joinpath(f'{vibemon.name.lower()}.png').open(mode='wb') as f:
        f.write(sprites)

    # Write the individual cutouts
    # TODO: tight cropping, more scientific splitting.
    with Image.open(io.BytesIO(removed)) as sheet:
        w, h = sheet.size
        step = w // 3
        for i in range(3):
            box = (i * step, 0, (i + 1) * step, h)
            sheet.crop(box).save(img_dir / f"{vibemon.name.lower()}_pose{i + 1}.png")

    rich_console.print(vibemon)


if __name__ == "__main__":
    asyncio.run(main())
