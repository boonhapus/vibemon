"""Terrascope WMTS constants for ESA WorldCover 2021 point sampling."""

from typing import Final

PROVIDER_NAME: Final[str] = "terrascope.worldcover_wmts"

WMTS_BASE_URL: Final[str] = "https://wmts.terrascope.be/wmts"
WORLDCOVER_LAYER: Final[str] = "esa-worldcover-map-10m-2021-v2_map"
WORLDCOVER_TIME: Final[str] = "2021-01-01"
WORLDCOVER_ZOOM: Final[int] = 13

LEGEND_RGB_TOLERANCE: Final[int] = 2
