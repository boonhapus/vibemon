from __future__ import annotations

import structlog
from datetime import datetime

import niquests

from app.domain.context import GenerationContext, SourceData
from app.domain.fallback import datetime_only_source
from app.infra.providers.protocol import VibemonProvider

log = structlog.get_logger(__name__)

_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"


def _weather_summary(code: int | None) -> str:
    if code is None:
        return "unknown conditions"
    table: dict[int, str] = {
        0: "clear sky",
        1: "mainly clear",
        2: "partly cloudy",
        3: "overcast",
        45: "foggy",
        48: "depositing rime fog",
        51: "light drizzle",
        53: "drizzle",
        55: "dense drizzle",
        61: "slight rain",
        63: "rain",
        65: "heavy rain",
        71: "slight snow",
        73: "snow",
        75: "heavy snow",
        80: "rain showers",
        81: "moderate rain showers",
        82: "violent rain showers",
        95: "thunderstorm",
        96: "thunderstorm with slight hail",
        99: "thunderstorm with heavy hail",
    }
    return table.get(int(code), "mixed conditions")


def _map_temperature_votes(temp_c: float) -> list[tuple[str, float]]:
    if temp_c < 5:
        return [("Ice", 0.9)]
    if temp_c < 15:
        return [("Water", 0.7)]
    if temp_c < 25:
        return [("Grass", 0.5)]
    if temp_c < 35:
        return [("Fire", 0.7)]
    return [("Ground", 0.9)]


def _hue_from_temperature(temp_c: float) -> float:
    t_min, t_max = -15.0, 45.0
    hue_cold, hue_hot = 190.0, 10.0
    t = max(t_min, min(t_max, temp_c))
    u = (t - t_min) / (t_max - t_min)
    return (hue_cold + u * (hue_hot - hue_cold)) % 360.0


def _weather_to_source(
    *,
    temp_c: float,
    wind_kmh: float,
    precip_mm: float,
    humidity_pct: float,
    uv: float | None,
    weather_code: int | None,
    when: datetime,
    lat: float | None,
    lon: float | None,
) -> SourceData:
    votes = _map_temperature_votes(temp_c)
    if 0 <= when.hour <= 5:
        votes = votes + [("Dark", 0.6)]

    speed_factor = max(0.0, min(1.0, wind_kmh / 80.0))
    hp_factor = max(0.0, min(1.0, humidity_pct / 100.0))

    clearish = weather_code is not None and int(weather_code) in (0, 1, 2, 3)
    uv_val = 0.0 if uv is None else float(uv)
    attack_factor = 0.55
    if clearish and uv_val > 6:
        attack_factor = min(1.0, 0.55 + 0.35)

    defense_factor = 0.55
    if precip_mm > 5:
        defense_factor = min(1.0, defense_factor + 0.35)

    loc_hint = ""
    if lat is not None and lon is not None:
        loc_hint = f" near {lat:.1f}°, {lon:.1f}°"

    flavour = (
        f"{temp_c:.0f}°C, {_weather_summary(weather_code)}{loc_hint}"
    )

    return SourceData(
        hp_factor=hp_factor,
        attack_factor=attack_factor,
        defense_factor=defense_factor,
        speed_factor=speed_factor,
        element_votes=votes,
        hue_primary=_hue_from_temperature(temp_c),
        luminosity=0.55,
        flavour_text=flavour,
        raw={
            "weather_live": True,
            "temperature_c": temp_c,
            "wind_kmh": wind_kmh,
            "precipitation_mm": precip_mm,
            "relative_humidity_pct": humidity_pct,
            "uv_index": uv,
            "weather_code": weather_code,
        },
    )


class WeatherProvider(VibemonProvider):
    @property
    def source_id(self) -> str:
        return "weather"

    async def fetch(self, context: GenerationContext) -> SourceData:
        if context.latitude is None or context.longitude is None:
            return datetime_only_source(context.timestamp, context.latitude)

        params = {
            "latitude": context.latitude,
            "longitude": context.longitude,
            "current": (
                "temperature_2m,wind_speed_10m,precipitation,relative_humidity_2m,"
                "uv_index,weather_code"
            ),
        }
        try:
            async with niquests.AsyncSession() as session:
                r = await session.get(_OPEN_METEO, params=params, timeout=12)
            r.raise_for_status()
            payload = r.json()
            cur = payload.get("current") or {}
            temp = float(cur.get("temperature_2m", 15.0))
            wind = float(cur.get("wind_speed_10m", 0.0))
            precip = float(cur.get("precipitation", 0.0))
            humidity = float(cur.get("relative_humidity_2m", 50.0))
            uv = cur.get("uv_index")
            uv_f = float(uv) if uv is not None else None
            wcode = cur.get("weather_code")
            wc = int(wcode) if wcode is not None else None

            return _weather_to_source(
                temp_c=temp,
                wind_kmh=wind,
                precip_mm=precip,
                humidity_pct=humidity,
                uv=uv_f,
                weather_code=wc,
                when=context.timestamp,
                lat=context.latitude,
                lon=context.longitude,
            )
        except Exception as err:
            log.warning("weather_fetch_failed", error=repr(err))
            return datetime_only_source(context.timestamp, context.latitude)
