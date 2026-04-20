from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

import cattrs
import dotenv

from app.birth import birth_vibemon
from app.plugins.climate.provider import ClimateProvider
from app.plugins.protocol import Context
from app.plugins.spotify.provider import SpotifyProvider


def main() -> None:
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser(description="Birth a new Vibemon")
    parser.add_argument("--name", required=True, help="Name of the Vibemon")
    parser.add_argument("--description", required=True, help="User description / theme")
    parser.add_argument("--location", default="", help="Lat,lon string")
    parser.add_argument("--seed", default=None, help="Birth seed (defaults to name)")
    parser.add_argument("--providers", default="climate", help="Comma-separated provider names")
    args = parser.parse_args()

    providers = []
    enabled = [p.strip() for p in args.providers.split(",")]
    if "climate" in enabled:
        providers.append(ClimateProvider())
    if "spotify" in enabled:
        providers.append(SpotifyProvider())

    context = Context(
        birth_seed=args.seed or args.name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        location=args.location,
        enabled_providers=enabled,
    )

    vibemon = asyncio.run(birth_vibemon(args.name, args.description, context, providers))

    import json
    print(json.dumps(cattrs.unstructure(vibemon), indent=2))


if __name__ == "__main__":
    main()
