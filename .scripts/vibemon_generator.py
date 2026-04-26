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


def extract_sprites(sprite_sheet: bytes) -> dict[str, Image.Image]:
    """
    Extract 3 individual sprites from a horizontally-arranged sprite sheet.
    
    Algorithm:
    1. Open the image and find overall content bounds
    2. Divide the content area into 3 equal horizontal regions
    3. For each region, find tight bounds and crop
    4. Pad all sprites to the same dimensions
    
    Returns dict with keys: "perspective_player", "showcase", "opponent_perspective"
    """
    removed = rembg.remove(sprite_sheet, session=REMBG_SESSION)

    with Image.open(io.BytesIO(removed)) as sheet:
        w, h = sheet.size
        
        sheet_bbox = sheet.getbbox()
        if sheet_bbox is None:
            return {
                "perspective_player": Image.new("RGBA", (w // 3, h)),
                "showcase": Image.new("RGBA", (w // 3, h)),
                "opponent_perspective": Image.new("RGBA", (w // 3, h)),
            }
        
        content_left, content_top, content_right, content_bottom = sheet_bbox
        content_width = content_right - content_left
        
        third_width = content_width // 3
        
        sprites = []
        max_width = 0
        max_height = 0
        
        for i in range(3):
            region_left = content_left + (i * third_width)
            region_right = content_left + ((i + 1) * third_width)
            
            region = sheet.crop((region_left, content_top, region_right, content_bottom))
            region_bbox = region.getbbox()
            
            if region_bbox:
                tight = region.crop(region_bbox)
                sprites.append(tight)
                max_width = max(max_width, tight.width)
                max_height = max(max_height, tight.height)
        
        while len(sprites) < 3:
            sprites.append(Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0)))
        
        keys = ["perspective_player", "showcase", "opponent_perspective"]
        result = {}
        for key, sprite in zip(keys, sprites):
            canvas = Image.new("RGBA", (max_width, max_height), (0, 0, 0, 0))
            canvas.paste(sprite, (0, 0))
            result[key] = canvas
        
        return result


async def main() -> None:
    dotenv.load_dotenv()

    if not os.environ.get("WEATHER_API_KEY"):
        rich_console.print("[red]Set WEATHER_API_KEY (WeatherAPI.com).[/red]")
        sys.exit(1)

    # AMAZON RAINFOREST
    # lat = float(os.environ.get("VIBEMON_LAT", "-4.0000"))
    # lon = float(os.environ.get("VIBEMON_LON", "-63.0000"))

    # LAS VEGAS
    lat = float(os.environ.get("VIBEMON_LAT", "36.1159"))
    lon = float(os.environ.get("VIBEMON_LON", "-115.1719"))

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

    img_dir = pathlib.Path(__file__).parent
    
    with img_dir.joinpath(f'{vibemon.name.lower()}.png').open(mode='wb') as f:
        f.write(sprites)

    for key, sprite in extract_sprites(sprite_sheet=sprites).items():
        sprite.save(img_dir / f"{vibemon.name.lower()}_{key}.png")

    rich_console.print(vibemon)


if __name__ == "__main__":
    asyncio.run(main())
