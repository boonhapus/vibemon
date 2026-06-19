"""Terrascope WMTS constants for ESA WorldCover 2021 point sampling."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "terrascope.worldcover_wmts"

QUOTA_KEY: Final[str] = "terrascope.worldcover"
RATE_LIMITS: Final[tuple[tuple[int, dt.timedelta], ...]] = ((120, dt.timedelta(minutes=1)),)

WMTS_BASE_URL: Final[str] = "https://wmts.terrascope.be/wmts"
WORLDCOVER_LAYER: Final[str] = "esa-worldcover-map-10m-2021-v2_map"
WORLDCOVER_TIME: Final[str] = "2021-01-01"
WORLDCOVER_ZOOM: Final[int] = 13

LEGEND_RGB_TOLERANCE: Final[int] = 2
