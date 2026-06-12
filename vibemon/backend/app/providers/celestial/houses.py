"""Placidus house cusps from Julian day and geographic coordinates."""

import datetime as dt
import math


def julian_day(timestamp_utc: dt.datetime) -> float:
    year = timestamp_utc.year
    month = timestamp_utc.month
    day = timestamp_utc.day
    hour = (
        timestamp_utc.hour
        + timestamp_utc.minute / 60.0
        + timestamp_utc.second / 3600.0
        + timestamp_utc.microsecond / 3_600_000_000.0
    )
    if month <= 2:
        year -= 1
        month += 12
    century = year // 100
    b = 2 - century + century // 4
    return int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5 + hour / 24.0


def obliquity_radians(jd: float) -> float:
    centuries = (jd - 2451545.0) / 36525.0
    degrees = 23.439291 - 0.0130042 * centuries
    return math.radians(degrees)


def greenwich_mean_sidereal_degrees(jd: float) -> float:
    centuries = (jd - 2451545.0) / 36525.0
    gmst = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * centuries * centuries
        - centuries**3 / 38_710_000.0
    )
    return gmst % 360.0


def right_ascension_to_longitude(ra_deg: float, obliquity: float) -> float:
    ra = math.radians(ra_deg)
    return math.degrees(math.atan2(math.sin(ra), math.cos(ra) * math.cos(obliquity))) % 360.0


def ascendant_longitude(ramc_deg: float, latitude: float, obliquity: float) -> float:
    ramc = math.radians(ramc_deg)
    numerator = math.sin(ramc)
    denominator = math.cos(ramc) * math.cos(obliquity) - math.sin(obliquity) * math.tan(latitude)
    return math.degrees(math.atan2(numerator, denominator)) % 360.0


def ascension_difference(ra_deg: float, latitude: float, obliquity: float) -> float:
    ra = math.radians(ra_deg)
    declination = math.asin(max(-1.0, min(1.0, math.sin(ra) * math.tan(obliquity))))
    return math.degrees(math.asin(max(-1.0, min(1.0, math.tan(latitude) * math.tan(declination)))))


def placidus_intermediate_ra(
    ramc_deg: float,
    latitude: float,
    obliquity: float,
    *,
    third: int,
    diurnal: bool,
) -> float:
    ra = ramc_deg + 30.0
    for _ in range(50):
        ad = ascension_difference(ra, latitude, obliquity)
        semi_arc = 90.0 + ad if diurnal else 90.0 - ad
        segment = semi_arc * third / 3.0
        ra_new = ramc_deg + segment if diurnal else ramc_deg + 180.0 - segment
        delta = (ra_new - ra + 180.0) % 360.0 - 180.0
        if abs(delta) < 1e-8:
            return ra_new
        ra = ra_new
    return ra


def placidus_cusps(*, jd: float, latitude_deg: float, longitude_deg: float) -> tuple[float, ...]:
    """Return twelve Placidus cusp longitudes indexed 0..11 for houses 1..12."""
    latitude = math.radians(latitude_deg)
    obliquity = obliquity_radians(jd)
    ramc = (greenwich_mean_sidereal_degrees(jd) + longitude_deg) % 360.0

    asc = ascendant_longitude(ramc, latitude, obliquity)
    mc = right_ascension_to_longitude(ramc, obliquity)
    ic = (mc + 180.0) % 360.0
    dsc = (asc + 180.0) % 360.0

    try:
        cusp_11 = right_ascension_to_longitude(
            placidus_intermediate_ra(ramc, latitude, obliquity, third=1, diurnal=True),
            obliquity,
        )
        cusp_12 = right_ascension_to_longitude(
            placidus_intermediate_ra(ramc, latitude, obliquity, third=2, diurnal=True),
            obliquity,
        )
        cusp_2 = right_ascension_to_longitude(
            placidus_intermediate_ra(ramc, latitude, obliquity, third=2, diurnal=False),
            obliquity,
        )
        cusp_3 = right_ascension_to_longitude(
            placidus_intermediate_ra(ramc, latitude, obliquity, third=1, diurnal=False),
            obliquity,
        )
    except ValueError:
        step = 30.0
        return tuple((asc + step * index) % 360.0 for index in range(12))

    cusp_5 = (cusp_11 + 180.0) % 360.0
    cusp_6 = (cusp_12 + 180.0) % 360.0
    cusp_8 = (cusp_2 + 180.0) % 360.0
    cusp_9 = (cusp_3 + 180.0) % 360.0

    return (
        asc,
        cusp_2,
        cusp_3,
        ic,
        cusp_5,
        cusp_6,
        dsc,
        cusp_8,
        cusp_9,
        mc,
        cusp_11,
        cusp_12,
    )


def house_for_longitude(longitude_deg: float, cusps: tuple[float, ...]) -> int:
    lon = longitude_deg % 360.0
    for index in range(12):
        start = cusps[index]
        end = cusps[(index + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return index + 1
        elif lon >= start or lon < end:
            return index + 1
    return 1
