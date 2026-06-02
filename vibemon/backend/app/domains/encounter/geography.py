"""Geography helpers for wild encounter bucket selection."""

from dataclasses import dataclass

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


@dataclass(frozen=True)
class GeoBox:
    """Latitude/longitude bounding box for a geohash cell."""

    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    @property
    def lat_span(self) -> float:
        return self.lat_max - self.lat_min

    @property
    def lon_span(self) -> float:
        return self.lon_max - self.lon_min


def geohash_encode(lat: float, lon: float, *, precision: int = 5) -> str:
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    geohash: list[str] = []
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            lon_mid = (lon_min + lon_max) / 2.0
            if lon >= lon_mid:
                ch = (ch << 1) | 1
                lon_min = lon_mid
            else:
                ch = ch << 1
                lon_max = lon_mid
        else:
            lat_mid = (lat_min + lat_max) / 2.0
            if lat >= lat_mid:
                ch = (ch << 1) | 1
                lat_min = lat_mid
            else:
                ch = ch << 1
                lat_max = lat_mid
        even = not even
        bit += 1
        if bit == 5:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def geohash_bbox(geohash: str) -> GeoBox:
    lat_min, lat_max = -90.0, 90.0
    lon_min, lon_max = -180.0, 180.0
    even = True
    for char in geohash:
        value = _BASE32.index(char)
        for shift in (4, 3, 2, 1, 0):
            bit = (value >> shift) & 1
            if even:
                lon_mid = (lon_min + lon_max) / 2.0
                if bit == 1:
                    lon_min = lon_mid
                else:
                    lon_max = lon_mid
            else:
                lat_mid = (lat_min + lat_max) / 2.0
                if bit == 1:
                    lat_min = lat_mid
                else:
                    lat_max = lat_mid
            even = not even
    return GeoBox(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)


def geohash_ring(center: str, *, ring: int) -> set[str]:
    """Return neighboring geohashes in the requested ring distance."""
    if ring < 0:
        raise ValueError("ring must be >= 0")
    if ring == 0:
        return {center}
    box = geohash_bbox(center)
    lat_step = box.lat_span
    lon_step = box.lon_span
    lat_mid = (box.lat_min + box.lat_max) / 2.0
    lon_mid = (box.lon_min + box.lon_max) / 2.0
    precision = len(center)
    out: set[str] = set()
    for dy in range(-ring, ring + 1):
        for dx in range(-ring, ring + 1):
            if max(abs(dx), abs(dy)) != ring:
                continue
            neighbor_lat = lat_mid + (lat_step * dy)
            neighbor_lon = lon_mid + (lon_step * dx)
            out.add(geohash_encode(neighbor_lat, neighbor_lon, precision=precision))
    out.discard(center)
    return out
