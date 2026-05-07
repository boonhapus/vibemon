import collections
import functools as ft
import itertools as it
import math
import statistics
from typing import Annotated, ClassVar

import niquests
import structlog

from app.balance.formulas import base_stat_asymmetric_scaling
from app.balance.element_chart import get_move_assignment_bonus
from app.plugins.provider import VibeProvider
from app.plugins.helpers import Signal, filter_element_types
from app.types import VibemonTypeT
from app import schema, utils

from .const import WeatherCode
from . import _weather, moves

_LOGGER = structlog.get_logger(__name__)


class ClimateProvider(VibeProvider):
    """
    A Vibemon is born from the sky above its birthplace.

    Open-Meteo's daily forecast at the trainer's coordinates becomes genetic
    material, folding live weather signals into a `schema.Affinity`.

    Six continuous signals route directly to base stats: temperature (HP),
    wind gusts (Attack), elevation (Defense), radiation (Sp. Attack),
    precipitation (Sp. Defense), and sustained wind (Speed).

    The result is that a creature born in a Death Valley heatwave has a
    fundamentally different soul than one from an Andean snowstorm or London
    fog—both stats and flavor emergent from the actual sky at birth.
    """

    name = "climate"

    exposed_elements: ClassVar[list[Annotated[VibemonTypeT, str]]] = [
        Annotated[VibemonTypeT.NORMAL, "overcast skies without precipitation"],
        Annotated[VibemonTypeT.FIRE, "solar radiation or extreme heat"],
        Annotated[VibemonTypeT.WATER, "precipitation (rain, drizzle, freezing rain)"],
        Annotated[VibemonTypeT.GRASS, "evapotranspiration or humid dew points"],
        Annotated[VibemonTypeT.ICE, "sub-freezing temperatures or snowfall"],
        Annotated[VibemonTypeT.FLYING, "sustained winds (15+ km/h)"],
        Annotated[VibemonTypeT.FIGHTING, "violent wind gusts (35+ km/h)"],
        Annotated[VibemonTypeT.GROUND, "mineral dust or dry exposed topsoil"],
        Annotated[VibemonTypeT.STEEL, "high atmospheric pressure systems"],
        Annotated[VibemonTypeT.FAIRY, "UV radiation exposure"],
        Annotated[VibemonTypeT.POISON, "air pollution concentration"],
        Annotated[VibemonTypeT.PSYCHIC, "barometric pressure swings"],
        Annotated[VibemonTypeT.DARK, "low visibility or heavy overcast"],
        Annotated[VibemonTypeT.GHOST, "fog or low visibility under low-UV conditions"],
        Annotated[VibemonTypeT.BUG, "humid tropical heat"],
        Annotated[VibemonTypeT.ROCK, "elevation or hail events"],
        Annotated[VibemonTypeT.DRAGON, "convective instability (CAPE)"],
        Annotated[VibemonTypeT.ELECTRIC, "thunderstorms"],
    ]

    def __init__(self) -> None:
        self.client = _weather.OpenMeteoAPIClient()

    def calculate_intensity(self, daily: dict[str, list[float]], *, index: int) -> float:
        """
        Calculates a normalized weather intensity score (0.0 to 1.0) for a specific day.

        Computes Z-scores across extreme weather signals to identify the most extreme
        outlier. The maximum absolute deviation is passed through a sigmoid function,
        where 0.5 represents an average day, values > 0.5 indicate high intensity,
        and values < 0.5 indicate unusually low intensity.

        Signals: temperature extremes (heat/cold), precipitation, wind gusts, convective
        potential, and visibility degradation.
        """
        # Aggregate signals representing intense weather
        temp_max = daily["temperature_2m_max"]
        temp_min = daily["temperature_2m_min"]
        precip = daily["precipitation_sum"]
        wind_gusts = daily["wind_gusts_10m_max"]
        cape = daily["cape_mean"]

        # Visibility inverted: low visibility (fog/storms) = high intensity
        visibility_inverted = [50.0 - v for v in daily["visibility_mean"]]

        def z_score(values: list[float]) -> float:
            if len(values) < 2 or not (stdev := statistics.stdev(values)):
                return 0.0
            return (values[index] - statistics.mean(values)) / stdev

        # Find max absolute deviation across all intensity signals
        deviations = [
            z_score(temp_max),
            z_score(temp_min),
            z_score(precip),
            z_score(wind_gusts),
            z_score(cape),
            z_score(visibility_inverted),
        ]
        deviation = max(deviations, key=abs)
        return round(number=1.0 / (1.0 + math.exp(-deviation)), ndigits=4)

    def determine_element_scores(
        self,
        signals: dict[str, Signal],
        weather_code: WeatherCode | None = None,
    ) -> dict[VibemonTypeT, float]:
        """
        Two-stage element scoring system.

        1. Map continuous data from the weather, clamp(min=0, max=1)
        2. Give flat bonuses based on WeatherCode, unclamped raw bonus.

        WeatherCode bonuses are additive because they confirm observed event
        categories rather than composing continuous environmental signals.
        """
        score: collections.defaultdict[VibemonTypeT, float] = collections.defaultdict(float)

        # Normal: cloud_cover > 60% AND no precipitation
        # Cloud cover: thresh=0.6 (60%) — overcast sky threshold; meteorologically standard
        # Precipitation (inverted): thresh=0.1 mm — no rain bonus; below 0.1mm = dry conditions
        cloud_cover_score = signals["clouds"].ramp("N", thresh=0.6, reach=0.4)
        dry_condition_bonus = signals["precip"].ramp("R", thresh=0.1, reach=0.1, invert=True)
        score[VibemonTypeT.NORMAL] += cloud_cover_score * dry_condition_bonus

        # Fire: radiation OR temp_max > 30°C
        # Radiation: thresh=0.65 (N) — strong sun at ~21 MJ/m² (normalized across 1–32 range);
        # raised from 0.50 to keep moderate-sun temperate cities from defaulting to FIRE.
        solar_radiation_score = signals["radiat"].ramp("N", thresh=0.65, reach=0.35)
        heat_temperature_score = signals["tmp_hi"].ramp("R", thresh=32.0, reach=20.0)
        score[VibemonTypeT.FIRE] += max(solar_radiation_score, heat_temperature_score)

        # Water: precipitation > 1 mm
        # Precipitation: thresh=1.0 mm (R) — meaningful rain threshold; ramps across 0–50 mm range.
        # Raised from 0.15 mm — light drizzle was auto-triggering WATER on most cloudy-coastal
        # cities, inflating the type's prevalence. Sustained rain still wins.
        score[VibemonTypeT.WATER] += signals["precip"].ramp("R", thresh=1.0, reach=49.0)

        # Grass: ET0 OR dew_point saturation
        # ET0: thresh=0.30 (N) — active plant growth at ~3.6 mm/day (normalized across 0–12 range)
        # Dew point: thresh=0.75 (N) — tropical humidity at ~17°C+ (normalized across -20–30 range)
        # Slightly tightened from 0.25/0.70 — GRASS was edging out FIRE for primary slot in
        # warm-temperate cities; the new thresholds keep tropics/jungles but trim fringe spawns.
        plant_evapotrans_score = signals["transp"].ramp("N", thresh=0.30, reach=0.70)
        humid_saturation_score = signals["dew_pt"].ramp("N", thresh=0.75, reach=0.25)
        score[VibemonTypeT.GRASS] += max(plant_evapotrans_score, humid_saturation_score)

        # Ice: sub-freezing temps OR active snowfall
        # Temperature min (inverted): thresh=0.0°C (R) — freezing point; full credit below 0, fades at -30°C
        # Snowfall: thresh=0.5 cm (R) — any meaningful accumulation; saturates at 10 cm/day
        # max() so a snowstorm in a city with above-freezing daytime min still triggers ICE.
        cold_temp_score = signals["tmp_lo"].ramp("R", thresh=0.0, reach=30.0, invert=True)
        snowfall_score = signals["snowfl"].ramp("R", thresh=0.5, reach=9.5)
        score[VibemonTypeT.ICE] += max(cold_temp_score, snowfall_score)

        # Flying: wind_speed > 10 km/h
        # Wind speed: thresh=10 km/h (R) — light-breeze threshold; ramps to 50 km/h gale-force.
        # Tuned between 12 km/h (under-represented) and 8 km/h (over-represented as secondary).
        score[VibemonTypeT.FLYING] += signals["windsp"].ramp("R", thresh=10.0, reach=40.0)

        # Fighting: wind_gusts > 30 km/h
        # Wind gusts: thresh=30 km/h (R) — strong gust threshold; ramps to 85 km/h structural damage
        score[VibemonTypeT.FIGHTING] += signals["windgu"].ramp("R", thresh=30.0, reach=55.0)

        # Steel: atmospheric pressure (high pressure systems)
        # Pressure: thresh=0.64 (N) — high-pressure systems >1025 hPa (normalized across 980–1050 range)
        score[VibemonTypeT.STEEL] += signals["pressr"].ramp("N", thresh=0.64, reach=0.36)

        # Fairy: UV radiation in clean, untouched air (pristine sun)
        # UV index: thresh=0.30 (N) — strong UV at 4-5 range (normalized across 0–14 range)
        # Pollution gate: PM2.5 attenuates the score so polluted hot cities trend FIRE, not FAIRY
        uv_score = signals["uv_idx"].ramp("N", thresh=0.30, reach=0.65)
        clean_air_factor = 1.0 - signals["pollut"].ramp("N", thresh=0.05, reach=0.20)
        score[VibemonTypeT.FAIRY] += uv_score * clean_air_factor

        # Poison: air pollution concentration
        # PM2.5: thresh=0.12 (N) — elevated pollution at 8 µg/m³ (normalized across 0–100 range)
        score[VibemonTypeT.POISON] += signals["pollut"].ramp("N", thresh=0.12, reach=0.95)

        # Dark: visibility < 10 km
        # Visibility (inverted): thresh=10 km (R) — poor visibility threshold; full credit below 10 km
        score[VibemonTypeT.DARK] += signals["visibl"].ramp("R", thresh=10.0, reach=10.0, invert=True)

        # Ghost: low visibility in low-UV conditions (spectral, not urban smog)
        # Visibility (inverted): thresh=10 km (R) — fog/mist threshold
        # Low-light gate: partial — full UV halves the score (midday haze still slightly spectral)
        # rather than zeroing it out (radiation fog burns off mid-morning, but the dawn fog still counts).
        visibility_score = signals["visibl"].ramp("R", thresh=10.0, reach=6.0, invert=True)
        low_light_factor = 1.0 - 0.5 * signals["uv_idx"].ramp("N", thresh=0.30, reach=0.65)
        score[VibemonTypeT.GHOST] += visibility_score * low_light_factor

        # Bug: humidity > 70% AND temp_max > 25°C — geometric mean preserves "must be both"
        # without the harsh compounding of pure multiplication (which left dry-desert at 0
        # but also crushed Singapore-tier tropics to ~0.1).
        # Humidity: thresh=70% (R) — tropical humidity; ramps from 40% to 100%
        # Temperature max: thresh=25°C (R) — tropical heat threshold; ramps from 0° to 50°C
        humid_stress_factor = signals["humdty"].ramp("R", thresh=70.0, reach=30.0)
        heat_stress_factor = signals["tmp_hi"].ramp("R", thresh=25.0, reach=25.0)
        score[VibemonTypeT.BUG] += math.sqrt(humid_stress_factor * heat_stress_factor)

        # Rock: elevation (geographic altitude)
        # Elevation: thresh=600 m (R) — highland threshold; ramps across full range to 4500 m
        score[VibemonTypeT.ROCK] += signals["elevat"].ramp("R", thresh=600.0, reach=4500.0)

        # Ground: mineral dust OR dry exposed topsoil
        # Dust: thresh=20 µg/m³ (R) — meaningful mineral-dust loading; saturates near severe events.
        # Soil moisture (inverted): thresh=0.18 m³/m³ (R) — dry topsoil signal; neutral default if missing.
        # Precipitation gate: rain suppresses exposed-dry-ground affinity without creating it.
        # Heat attenuator: extreme heat partially redirects dry desert conditions toward FIRE.
        dust_score = signals["dust"].ramp("R", thresh=20.0, reach=130.0)
        dry_topsoil_score = signals["soilmt"].ramp("R", thresh=0.18, reach=0.18, invert=True)
        dry_weather_gate = 1.0 - signals["precip"].ramp("R", thresh=1.0, reach=9.0)
        scorching_heat_attenuator = 1.0 - 0.5 * signals["tmp_hi"].ramp("R", thresh=32.0, reach=20.0)
        exposed_ground_score = dry_topsoil_score * dry_weather_gate * scorching_heat_attenuator
        score[VibemonTypeT.GROUND] += max(dust_score, exposed_ground_score)

        # Psychic: daily barometric pressure volatility
        # Pressure range: thresh=8 hPa (R) — notable synoptic pressure movement; saturates at 30 hPa/day.
        # Uses range rather than high pressure so STEEL keeps stable anticyclones.
        score[VibemonTypeT.PSYCHIC] += signals["pressrng"].ramp("R", thresh=8.0, reach=22.0)

        # Electric: atmospheric instability (storm potential)
        # CAPE: thresh=0.35 (N) — strong thunderstorm threshold at 1750 J/kg (normalized across 0–5000 range)
        # Selective signal for electrical affinity; higher threshold than DRAGON but full scale capability
        score[VibemonTypeT.ELECTRIC] += signals["cape_m"].ramp("N", thresh=0.35, reach=0.65)

        # Dragon: convective instability OR mountain altitude (mythic mountain-storm dweller)
        # CAPE: thresh=0.30 (N) — severe weather potential at 1500 J/kg (normalized across 0–5000 range)
        # Elevation: thresh=2000 m (R) — kicks in above ROCK's mid-range; saturates at 5000 m
        cape_score = signals["cape_m"].ramp("N", thresh=0.30, reach=0.70)
        altitude_score = signals["elevat"].ramp("R", thresh=2000.0, reach=3000.0)
        score[VibemonTypeT.DRAGON] += max(cape_score, altitude_score)

        # General Tier structure:
        # - 0.2: LIGHT
        # - 0.3: MODERATE
        # - 0.4: HEAVY
        # - 0.5: RARE
        match weather_code:
            # Clear skies: solar heating (FIRE) + fair/stable weather (NORMAL)
            # FIRE bonus halved (0.2 → 0.1) — CLEAR_SKY is the most common WMO code globally,
            # so the prior bonus was a primary driver of FIRE over-representation.
            case WeatherCode.CLEAR_SKY | WeatherCode.MAINLY_CLEAR:
                score[VibemonTypeT.FIRE] += 0.1
                score[VibemonTypeT.NORMAL] += 0.2

            # Partial clouds confirm baseline overcast → NORMAL element
            case WeatherCode.PARTLY_CLOUDY:
                score[VibemonTypeT.NORMAL] += 0.2

            # Heavy overcast confirms dark, cloudy conditions
            case WeatherCode.OVERCAST:
                score[VibemonTypeT.NORMAL] += 0.3
                score[VibemonTypeT.DARK] += 0.2

            # All thunderstorm variants confirm electrical activity (rare event)
            case WeatherCode.THUNDERSTORM | WeatherCode.THUNDERSTORM_WITHOUT_PRECIP | WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY:  # fmt: skip # noqa: E501
                score[VibemonTypeT.ELECTRIC] += 0.5
                score[VibemonTypeT.DRAGON] += 0.30

            # Light hail: thunderstorm + ice/rock impact
            case WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL:
                score[VibemonTypeT.ELECTRIC] += 0.5
                score[VibemonTypeT.ROCK] += 0.3
                score[VibemonTypeT.DRAGON] += 0.20

            # Heavy hail: thunderstorm + strong ice/rock impact
            case WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL:
                score[VibemonTypeT.ELECTRIC] += 0.5
                score[VibemonTypeT.ROCK] += 0.4
                score[VibemonTypeT.DRAGON] += 0.30

            # Fog/rime confirm spectral conditions (rare event)
            case WeatherCode.FOG | WeatherCode.DEPOSITING_RIME_FOG:
                score[VibemonTypeT.GHOST] += 0.5

            # Light precipitation: drizzle + slight rain (common, weak signal)
            case WeatherCode.DRIZZLE_LIGHT | WeatherCode.DRIZZLE_MODERATE | WeatherCode.RAIN_SLIGHT | WeatherCode.RAIN_SHOWERS_SLIGHT:  # fmt: skip # noqa: E501
                score[VibemonTypeT.WATER] += 0.3

            # Moderate precipitation (common, medium signal)
            case WeatherCode.DRIZZLE_DENSE | WeatherCode.RAIN_MODERATE | WeatherCode.RAIN_SHOWERS_MODERATE:
                score[VibemonTypeT.WATER] += 0.4

            # Heavy precipitation (intense, strong signal)
            case WeatherCode.RAIN_HEAVY | WeatherCode.RAIN_SHOWERS_VIOLENT:
                score[VibemonTypeT.WATER] += 0.5

            # Freezing rain/drizzle split affinity between water (liquid) and ice (freezing)
            case WeatherCode.FREEZING_RAIN_LIGHT | WeatherCode.FREEZING_DRIZZLE_LIGHT | WeatherCode.FREEZING_DRIZZLE_DENSE:  # fmt: skip # noqa: E501
                score[VibemonTypeT.WATER] += 0.1
                score[VibemonTypeT.ICE] += 0.2

            case WeatherCode.FREEZING_RAIN_HEAVY:
                score[VibemonTypeT.WATER] += 0.2
                score[VibemonTypeT.ICE] += 0.3

            # Light snow (common, weak signal)
            case WeatherCode.SNOW_FALL_SLIGHT | WeatherCode.SNOW_SHOWERS_SLIGHT | WeatherCode.SNOW_GRAINS:
                score[VibemonTypeT.ICE] += 0.3

            # Moderate snow (common, medium signal)
            case WeatherCode.SNOW_FALL_MODERATE:
                score[VibemonTypeT.ICE] += 0.4

            # Heavy snow (intense, strong signal)
            case WeatherCode.SNOW_SHOWERS_HEAVY | WeatherCode.SNOW_FALL_HEAVY:
                score[VibemonTypeT.ICE] += 0.5

        # Give NORMAL a tiny bit of padding so we ensure that the move pool is available.
        score[VibemonTypeT.NORMAL] = score[VibemonTypeT.NORMAL] or 0.05

        return score

    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Translate raw API data to Affinity components."""
        # TODO: use asyncio.gather when upgraded to paid OpenMeteo.
        wr = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        ar = await self.client.air_quality(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])

        try:
            wr.raise_for_status()
            ar.raise_for_status()
        except niquests.HTTPError as e:
            self._log_http_error(e)

        d = wr.json()
        s = d["daily"]
        i = -1

        # ── DATA MUNGING ──────────────────────────────────────────────────────────────

        def daily_means(times: list[str], values: list[float | None]) -> dict[str, float]:
            return {
                day: statistics.fmean(day_values)
                for day, group in it.groupby(zip(times, values), key=lambda tp: tp[0][:10])
                if (day_values := [value for _, value in group if value is not None])
            }

        air_quality_hourly = ar.json()["hourly"]
        weather_hourly = d["hourly"]
        pm25_by_day = daily_means(air_quality_hourly["time"], air_quality_hourly["pm2_5"])
        dust_by_day = daily_means(air_quality_hourly["time"], air_quality_hourly["dust"])
        soil_moisture_by_day = daily_means(weather_hourly["time"], weather_hourly["soil_moisture_0_to_1cm"])

        # INJECT HOURLY-DERIVED SIGNALS ONTO THE DAILY METRIC
        s["pm2_5_mean"] = [pm25_by_day.get(day, 0.0) for day in s["time"]]
        s["dust_mean"] = [dust_by_day.get(day, 0.0) for day in s["time"]]
        s["soil_moisture_0_to_1cm_mean"] = [soil_moisture_by_day.get(day, 0.18) for day in s["time"]]

        # ── /DATA MUNGING ─────────────────────────────────────────────────────────────

        # fmt: off
        # ruff: noqa: E501
        signals = {
            # tmp_hi: Daily max temperature (-20 to 50°C)
            # Min: coldest inhabited regions (Siberia winter). Max: hottest recorded (Death Valley ~54°C).
            # Routes to base HP stat; directly embodies creature's core vitality from birth climate.
            "tmp_hi": Signal(attr="temperature_2m_max", raw=s["temperature_2m_max"][i], min=-20.0, max=50.0),
            # tmp_lo: Daily min temperature (-30 to 40°C)
            # Min: extreme cold (polar regions). Max: tropical overnight lows.
            # Routes to Sp. Defense; modulates climate resilience via nocturnal conditions.
            "tmp_lo": Signal(attr="temperature_2m_min", raw=s["temperature_2m_min"][i], min=-30.0, max=40.0),
            # precip: Daily precipitation (0–50 mm)
            # Min: no rain. Max: heavy downpour; >50 mm/day approaches flood conditions.
            # Baseline for WATER element; split between WATER affinity and Sp. Defense offset.
            "precip": Signal(attr="precipitation_sum", raw=s["precipitation_sum"][i], min=0.0, max=50.0),
            # windsp: Sustained wind speed (3–50 km/h)
            # Min: calm breeze threshold. Max: strong sustained wind for stat-scaling purposes
            # (range compressed from 90 km/h — most populated cities cap well below 30 km/h, so
            # the wider range left base_speed clustered near floor). Type-scoring ramps still
            # use raw thresholds (12/30 km/h) so element selection is unaffected.
            "windsp": Signal(attr="wind_speed_10m_max", raw=s["wind_speed_10m_max"][i], min=3.0, max=50.0),
            # windgu: Wind gust peaks (5–70 km/h)
            # Min: light gust threshold. Max: strong gust for stat-scaling purposes (range
            # compressed from 120 km/h for the same reason as windsp). Type-scoring uses
            # raw thresholds (30 km/h FIGHTING) so element selection is unaffected.
            "windgu": Signal(attr="wind_gusts_10m_max", raw=s["wind_gusts_10m_max"][i], min=5.0, max=70.0),
            # uv_idx: Maximum UV index (0–14 scale)
            # Min: no UV (night/polar winter). Max: extreme tropical (WMO scale 11+, capped at 14).
            # Unobservable signal; normalized threshold at 0.21 (UV 3+ = sun protection needed).
            "uv_idx": Signal(attr="uv_index_max", raw=s["uv_index_max"][i], min=0.0, max=14.0),
            # radiat: Daily shortwave radiation sum (1–32 MJ/m²)
            # Min: deep overcast/tropical winter (~1 MJ/m²). Max: clear desert summer (~25–32 MJ/m²).
            # Routes to base Sp. Attack stat; creature's magical affinity from solar energy.
            "radiat": Signal(attr="shortwave_radiation_sum", raw=s["shortwave_radiation_sum"][i], min=1.0, max=32.0),
            # clouds: Mean cloud cover (0–100%)
            # Min: clear sky (0%). Max: completely overcast (100%).
            # Meteorologically standard 0–100 scale; feeds NORMAL element.
            "clouds": Signal(attr="cloud_cover_mean", raw=s["cloud_cover_mean"][i], min=0.0, max=100.0),
            # pressr: Mean sea-level pressure (980–1050 hPa)
            # Min: extreme low-pressure storm system. Max: Siberian high (>1050 hPa, capped at 1050).
            # Unobservable signal; normalized threshold at 0.64 (>1025 hPa = high pressure systems).
            "pressr": Signal(attr="pressure_msl_mean", raw=s["pressure_msl_mean"][i], min=980.0, max=1050.0),
            # pressrng: Daily sea-level pressure range (0–30 hPa)
            # Min: stable air mass. Max: strong synoptic transition/cyclone passage.
            # Feeds PSYCHIC affinity as barometric pattern-reading without overlapping STEEL's high-pressure signal.
            "pressrng": Signal(attr="pressure_msl_range", raw=s["pressure_msl_max"][i] - s["pressure_msl_min"][i], min=0.0, max=30.0),
            # transp: Evapotranspiration/Reference ET0 (0–12 mm/day)
            # Min: no plant activity (winter/dormant). Max: extreme irrigation demand (arid agriculture).
            # Unobservable signal; normalized threshold at 0.25 (3 mm/day = active plant growth).
            "transp": Signal(attr="et0_fao_evapotranspiration", raw=s["et0_fao_evapotranspiration"][i], min=0.0, max=12.0),
            # pollut: PM2.5 air pollution (0–100 µg/m³)
            # Min: clean air. Max: hazardous/emergency air quality (>100 µg/m³ = severe pollution).
            # Unobservable signal; normalized threshold at 0.15 (10 µg/m³ = WHO health damage threshold).
            "pollut": Signal(attr="pm2_5_mean", raw=s["pm2_5_mean"][i], min=0.0, max=100.0),
            # dust: Mineral dust aerosol concentration (0–300 µg/m³)
            # Min: no dust. Max: severe dust event. Direct path to GROUND affinity.
            "dust": Signal(attr="dust_mean", raw=s["dust_mean"][i], min=0.0, max=300.0),
            # visibl: Horizontal visibility (0–50 km)
            # Min: fog/mist visibility (0 km ~ dense fog). Max: exceptional clear-air visibility (~50 km).
            # Meteorologically standard; inverted for DARK element (low visibility = high affinity).
            "visibl": Signal(attr="visibility_mean", raw=s["visibility_mean"][i], min=0.0, max=50.0),
            # dew_pt: Mean dew point (-20 to 30°C)
            # Min: arid freezing (very dry, very cold). Max: tropical saturated air (~25–30°C).
            # Unobservable signal; normalized threshold at 0.70 (≈15°C = tropical humidity).
            "dew_pt": Signal(attr="dew_point_2m_mean", raw=s["dew_point_2m_mean"][i], min=-20.0, max=30.0),
            # cape_m: Convective Available Potential Energy (0–5000 J/kg)
            # Min: no convective potential (stable atmosphere). Max: extreme supercell CAPE (>4000 = destructive).
            # Unobservable signal; normalized threshold at 0.30 (1500 J/kg = severe weather potential).
            "cape_m": Signal(attr="cape_mean", raw=s["cape_mean"][i], min=0.0, max=5000.0),
            # humdty: Mean relative humidity (0–100%)
            # Min: bone-dry air (arid desert). Max: saturated air mass (tropical/monsoon regions).
            # Meteorologically standard 0–100 scale; combines with temp for BUG tropicality.
            "humdty": Signal(attr="relative_humidity_2m_mean", raw=s["relative_humidity_2m_mean"][i], min=0.0, max=100.0),
            # soilmt: Topsoil moisture (0–0.5 m³/m³)
            # Min: parched surface layer. Max: saturated/wet topsoil. Inverted for exposed-dry-ground affinity.
            "soilmt": Signal(attr="soil_moisture_0_to_1cm_mean", raw=s["soil_moisture_0_to_1cm_mean"][i], min=0.0, max=0.5),
            # elevat: Surface elevation above sea level (0–2000 m)
            # Min: sea level (0 m). Max: highland threshold for stat-scaling purposes
            # (range compressed from 4500 m — most populated cities sit below 200 m and the
            # wider range crushed base_defense to floor). Type-scoring ramps for ROCK/DRAGON
            # use raw thresholds (600/2000 m) so element selection is unaffected; high-altitude
            # cities (La Paz, Lhasa, Mexico City) intentionally peg base_defense at max.
            "elevat": Signal(attr="elevation", raw=d["elevation"], min=0.0, max=2000.0),
            # snowfl: Daily snowfall accumulation (0–20 cm)
            # Min: no snow. Max: heavy snow event (~20 cm/day = blizzard territory).
            # Secondary path to ICE element so winter cities trigger even when daily min temp
            # sits above freezing during a snowstorm warm-up.
            "snowfl": Signal(attr="snowfall_sum", raw=s["snowfall_sum"][i], min=0.0, max=20.0),
        }
        # fmt: on

        wmo_code = WeatherCode(s["weather_code"][i])
        rankings = self.determine_element_scores(signals=signals, weather_code=wmo_code)
        elements = filter_element_types(rankings)
        bonus_fx = ft.partial(get_move_assignment_bonus, vibemon_elements=elements)
        starters = {m: rankings[m.type] * bonus_fx(m.type) for m in moves.MOVES if m.level_requirement == 1}

        affinity = schema.Affinity(
            identity=schema.Identity(
                name="__",
                elements=elements,
                base_hp=base_stat_asymmetric_scaling(signals["tmp_hi"].normal, stat="hp"),
                base_attack=base_stat_asymmetric_scaling(signals["windgu"].normal, stat="attack"),
                # reshape(0.4): most cities near sea level, linear scaling crushed them
                # to floor. Concave-up lifts low values so median city lands ~0.5.
                base_defense=base_stat_asymmetric_scaling(signals["elevat"] ** 0.4, stat="defense"),
                # reshape(1.6): tropical cities with max solar radiation clustered
                # at ceiling of asymmetric scale. Concave-down spreads high values.
                base_sp_attack=base_stat_asymmetric_scaling(signals["radiat"] ** 1.6, stat="sp_attack"),
                # mix(): sp_defense needs both precip (30%) and nocturnal temp (70%),
                # not one-or-the-other. Blend clamped to avoid overshoot.
                base_sp_defense=base_stat_asymmetric_scaling(Signal.mix(signals["precip"] * 0.3, signals["tmp_lo"] * 0.7), stat="sp_defense"),  # fmt: skip # noqa: E501
                base_speed=base_stat_asymmetric_scaling(signals["windsp"].normal, stat="speed"),
            ),
            visual_notes=wmo_code.description,
            intensity=self.calculate_intensity(s, index=i),
            provider_id=self.name,
            moves=utils.weighted_sample(starters.keys(), starters.values(), k=10),
        )

        return affinity

    async def teardown(self) -> None:
        """Release provider-owned resources. Override only when needed."""
        await self.client.close()
