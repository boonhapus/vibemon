"""Skyfield ephemeris engine for birth-chart computation."""

from functools import lru_cache
from pathlib import Path
from typing import NamedTuple
import datetime as dt
import math

from skyfield import almanac
from skyfield.api import Loader, wgs84
from skyfield.jpllib import SpiceKernel
from skyfield.timelib import Time, Timescale

from app.core.math import angular_distance
from app.providers.celestial import const, houses
from app.providers.celestial import eclipse as eclipse_logic
from app.providers.celestial.aspects import detect_aspects
from app.providers.celestial.ephemeris import models
from app.providers.celestial.ephemeris import solar as solar_logic

_DATA_DIR = Path(__file__).resolve().parent / "data"
_BODY_TARGETS: tuple[tuple[str, str], ...] = (
    ("sun", "sun"),
    ("moon", "moon"),
    ("mercury", "mercury"),
    ("venus", "venus"),
    ("mars", "mars"),
    ("jupiter", "jupiter barycenter"),
    ("saturn", "saturn barycenter"),
)


class _EphemerisBundle(NamedTuple):
    eph: SpiceKernel
    timescale: Timescale


@lru_cache(maxsize=1)
def _ephemeris_bundle() -> _EphemerisBundle:
    loader = Loader(str(_DATA_DIR))
    return _EphemerisBundle(eph=loader("de421.bsp"), timescale=loader.timescale())


def sign_name(longitude_deg: float) -> str:
    index = int(longitude_deg // 30) % 12
    return const.ZODIAC_SIGNS[index]


def moon_illumination(sun_longitude: float, moon_longitude: float) -> float:
    separation = math.radians(angular_distance(sun_longitude, moon_longitude))
    return (1.0 - math.cos(separation)) / 2.0


def _mean_node_longitudes(jd: float) -> tuple[float, float]:
    centuries = (jd - 2451545.0) / 36525.0
    ascending = (125.044555 - 1934.1361849 * centuries) % 360.0
    return ascending, (ascending + 180.0) % 360.0


def _node_longitudes(time: Time, earth: object, moon: object, *, eph: SpiceKernel, jd: float) -> tuple[float, float]:
    window_start = time - 20.0
    window_end = time + 20.0
    times, events = almanac.find_discrete(window_start, window_end, almanac.moon_nodes(eph))
    ascending: list[float] = []
    descending: list[float] = []
    for node_time, event in zip(times, events, strict=True):
        apparent = earth.at(node_time).observe(moon).apparent()  # pyrefly: ignore
        longitude = apparent.ecliptic_latlon()[1].degrees
        if int(event) == 1:
            ascending.append(longitude)
        else:
            descending.append(longitude)
    if not ascending or not descending:
        return _mean_node_longitudes(jd)
    return ascending[len(ascending) // 2], descending[len(descending) // 2]


def compute_chart(
    *,
    timestamp: dt.datetime,
    latitude: float,
    longitude: float,
    timezone: dt.timezone,
) -> models.CelestialChart:
    eph, ts = _ephemeris_bundle()
    earth = eph["earth"]
    moon = eph["moon"]
    time = ts.from_datetime(timestamp.astimezone(dt.UTC))
    observer = earth + wgs84.latlon(latitude, longitude)
    solar = solar_logic.solar_band(
        timestamp=timestamp,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )

    jd = houses.julian_day(timestamp.astimezone(dt.UTC))
    house_cusps = houses.placidus_cusps(jd=jd, latitude_deg=latitude, longitude_deg=longitude)

    body_longitudes: dict[str, float] = {}
    bodies: list[models.BodyObservation] = []

    for name, target in _BODY_TARGETS:
        apparent = observer.at(time).observe(eph[target]).apparent()  # pyrefly: ignore
        _lat, lon, _distance = apparent.ecliptic_latlon()
        altitude = apparent.altaz()[0].degrees
        longitude_deg = lon.degrees
        body_longitudes[name] = longitude_deg
        bodies.append(
            models.BodyObservation(
                name=name,
                ecliptic_longitude=longitude_deg,
                altitude_deg=altitude,
                visible=altitude > 0.0,
                house=houses.house_for_longitude(longitude_deg, house_cusps),
                sign=sign_name(longitude_deg),
            )
        )

    ascending_node, descending_node = _node_longitudes(time, earth, moon, eph=eph, jd=jd)
    sun_longitude = body_longitudes["sun"]
    moon_longitude = body_longitudes["moon"]

    return models.CelestialChart(
        timestamp_iso=timestamp.astimezone(dt.UTC).isoformat(),
        latitude=latitude,
        longitude=longitude,
        timezone=str(timezone),
        solar_phase=solar.phase,
        twilight_prevalence=solar.twilight_prevalence,
        moon_illumination=moon_illumination(sun_longitude, moon_longitude),
        eclipse_season=eclipse_logic.in_eclipse_season(
            sun_longitude,
            ascending_node_longitude=ascending_node,
            descending_node_longitude=descending_node,
        ),
        house_cusps=house_cusps,
        bodies=tuple(bodies),
        aspects=detect_aspects(body_longitudes),
    )
