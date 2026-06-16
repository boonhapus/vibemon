"""Terrascope WMTS client for ESA WorldCover 2021 point sampling."""

from io import BytesIO
from typing import Any
import datetime as dt
import math

from PIL import Image
import structlog

from app.providers._api.hooks import LoggingHook, RateLimiterHook
from app.providers._api.policy import provider_default_headers, provider_retry_policy
from app.providers._api.session import CachedAPIClient
from app.providers.biome import const as biome_const
from app.storage.cache.redis import make_cache_backend

from . import const

_LOGGER = structlog.get_logger(__name__)


class TerrascopeWorldCoverClient(CachedAPIClient):
    """Fetch WorldCover classification tiles via Terrascope WMTS KVP."""

    provider_name = const.PROVIDER_NAME

    def __init__(self, **session_opts: Any) -> None:
        rate_limiter = RateLimiterHook(
            (120, dt.timedelta(minutes=1)),
            provider=TerrascopeWorldCoverClient.provider_name,
        )
        session_opts.setdefault("backend", make_cache_backend("terrascope_worldcover_wmts"))
        super().__init__(
            expire_after=dt.timedelta(days=30),
            base_url=const.WMTS_BASE_URL,
            hooks=LoggingHook(provider=TerrascopeWorldCoverClient.provider_name) + rate_limiter,  # pyrefly: ignore
            retries=provider_retry_policy(),
            **session_opts,
        )
        self.headers.update(provider_default_headers(accept="image/png"))

    @staticmethod
    def _latlon_to_tile(latitude: float, longitude: float, zoom: int) -> tuple[int, int]:
        tiles = 2**zoom
        tile_x = int((longitude + 180) / 360 * tiles)
        latitude_radians = math.radians(latitude)
        tile_y = int((1 - math.asinh(math.tan(latitude_radians)) / math.pi) / 2 * tiles)
        return tile_x, tile_y

    @staticmethod
    def _pixel_in_tile(
        latitude: float,
        longitude: float,
        zoom: int,
        tile_x: int,
        tile_y: int,
        size: int = 256,
    ) -> tuple[int, int]:
        tiles = 2**zoom
        x_fraction = (longitude + 180) / 360 * tiles
        latitude_radians = math.radians(latitude)
        y_fraction = (1 - math.asinh(math.tan(latitude_radians)) / math.pi) / 2 * tiles
        pixel_x = int((x_fraction - tile_x) * size)
        pixel_y = int((y_fraction - tile_y) * size)
        return max(0, min(size - 1, pixel_x)), max(0, min(size - 1, pixel_y))

    @classmethod
    def decode_rgb(cls, rgb: tuple[int, int, int]) -> biome_const.WorldCoverClassT:
        best_class, best_distance = biome_const.WorldCoverClassT.nearest_rgb(rgb)
        if best_distance > const.LEGEND_RGB_TOLERANCE**2 * 3:
            _LOGGER.warning("worldcover_unmapped_rgb", rgb=rgb, nearest=best_class.value, distance=best_distance)
        return best_class

    @classmethod
    def classify_tile_at_point(
        cls,
        image: Image.Image,
        *,
        latitude: float,
        longitude: float,
        tile_x: int,
        tile_y: int,
        zoom: int,
    ) -> biome_const.WorldCoverClassT:
        width, height = image.size
        if width < 2 or height < 2:
            return biome_const.WorldCoverClassT.PERMANENT_WATER
        pixel_x, pixel_y = cls._pixel_in_tile(latitude, longitude, zoom, tile_x, tile_y, size=width)
        pixel = image.getpixel((pixel_x, pixel_y))
        if not isinstance(pixel, tuple):
            raise RuntimeError("WorldCover tile pixel was not an RGBA tuple")
        red, green, blue, alpha = pixel
        if alpha < 10:
            return biome_const.WorldCoverClassT.PERMANENT_WATER
        return cls.decode_rgb((red, green, blue))

    async def sample_class(self, latitude: float, longitude: float) -> biome_const.WorldCoverClassT:
        tile_x, tile_y = self._latlon_to_tile(latitude, longitude, const.WORLDCOVER_ZOOM)
        params = {
            "SERVICE": "WMTS",
            "REQUEST": "GetTile",
            "VERSION": "1.0.0",
            "LAYER": const.WORLDCOVER_LAYER,
            "STYLE": "default",
            "TIME": const.WORLDCOVER_TIME,
            "TILEMATRIXSET": "EPSG:3857",
            "TILEMATRIX": str(const.WORLDCOVER_ZOOM),
            "TILEROW": str(tile_y),
            "TILECOL": str(tile_x),
            "FORMAT": "image/png",
        }
        response = await self.get("", params=params)
        response.raise_for_status()
        content = response.content
        if content is None:
            raise RuntimeError("WorldCover tile response had no content")
        image = Image.open(BytesIO(content)).convert("RGBA")
        return self.classify_tile_at_point(
            image,
            latitude=latitude,
            longitude=longitude,
            tile_x=tile_x,
            tile_y=tile_y,
            zoom=const.WORLDCOVER_ZOOM,
        )
