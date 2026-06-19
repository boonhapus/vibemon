"""OSM Overpass API constants for marine and inland water proximity."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "overpass.api"

QUOTA_KEY: Final[str] = "overpass"
RATE_LIMITS: Final[tuple[tuple[int, dt.timedelta], ...]] = ((30, dt.timedelta(minutes=1)),)

OVERPASS_ENDPOINTS: Final[tuple[str, ...]] = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
SEARCH_RADIUS_M: Final[int] = 30_000

MARINE_QUERY: Final[str] = """[out:json][timeout:25];
(
  way["natural"="coastline"](around:{radius},{lat},{lon});
  relation["natural"="coastline"](around:{radius},{lat},{lon});
  way["natural"="bay"](around:{radius},{lat},{lon});
  node["natural"="coastline"](around:{radius},{lat},{lon});
  way["natural"="water"]["water"="lake"](around:{radius},{lat},{lon});
  relation["natural"="water"]["water"="lake"](around:{radius},{lat},{lon});
);
out geom tags;"""

INLAND_QUERY: Final[str] = """[out:json][timeout:25];
(
  way["waterway"](around:{radius},{lat},{lon});
  way["natural"="water"](around:{radius},{lat},{lon});
  relation["natural"="water"](around:{radius},{lat},{lon});
);
out geom tags;"""
