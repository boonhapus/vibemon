from typing import ClassVar
import asyncio
import collections
import datetime as dt
import itertools as it
import math
import statistics

import structlog

from app.core.math import clamp
from app.domains.generation.affinity import Affinity
from app.domains.generation.merge import filter_element_types
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import Identity
from app.providers import catalog_schema as catalog
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider
from app.providers.helpers import Signal, pick_starter_moves

from . import schema as climate_schema
from .const import WeatherCode
from .openmeteo import api as openmeteo_api
from .openmeteo import schema as openmeteo_schema

_LOGGER = structlog.get_logger(__name__)

_WINDY_WEATHER_CODES = frozenset(
    {
        WeatherCode.RAIN_SHOWERS_VIOLENT,
        WeatherCode.THUNDERSTORM,
        WeatherCode.THUNDERSTORM_WITHOUT_PRECIP,
        WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY,
        WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL,
        WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL,
    }
)

_SNOW_WEATHER_CODES = frozenset(
    {
        WeatherCode.SNOW_FALL_SLIGHT,
        WeatherCode.SNOW_FALL_MODERATE,
        WeatherCode.SNOW_FALL_HEAVY,
        WeatherCode.SNOW_GRAINS,
        WeatherCode.SNOW_SHOWERS_SLIGHT,
        WeatherCode.SNOW_SHOWERS_HEAVY,
        WeatherCode.DEPOSITING_RIME_FOG,
        WeatherCode.FREEZING_DRIZZLE_LIGHT,
        WeatherCode.FREEZING_DRIZZLE_DENSE,
        WeatherCode.FREEZING_RAIN_LIGHT,
        WeatherCode.FREEZING_RAIN_HEAVY,
    }
)

_STORM_WEATHER_CODES = frozenset(
    {
        WeatherCode.THUNDERSTORM,
        WeatherCode.THUNDERSTORM_WITHOUT_PRECIP,
        WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY,
        WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL,
        WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL,
    }
)


class ClimateProvider(VibeProvider[climate_schema.ClimatePayload]):
    """
    A Vibemon remembers the weather drifting overhead when it hatched.

    Hatched under linoleum-bright desert noon, Highland drizzle, or pea-soup fog
    over the boulevard - each one reads differently, the way a Sunday paper
    weather box can change block to block.
    """

    name = "climate"
    display_label = "SKY"
    tagline = "Heat, haze, and the air overhead."

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "overcast skies without precipitation"),
        (VibemonTypeT.FIRE, "solar radiation or extreme heat"),
        (VibemonTypeT.WATER, "precipitation (rain, drizzle, freezing rain)"),
        (VibemonTypeT.GRASS, "evapotranspiration or humid dew points"),
        (VibemonTypeT.ICE, "sub-freezing temperatures or snowfall"),
        (VibemonTypeT.FLYING, "sustained winds (15+ km/h)"),
        (VibemonTypeT.FIGHTING, "violent gust spikes and impact weather"),
        (VibemonTypeT.GROUND, "mineral dust or arid exposed earth"),
        (VibemonTypeT.FAIRY, "clean air and bright UV in clear or misty sun"),
        (VibemonTypeT.POISON, "air pollution concentration"),
        (VibemonTypeT.DARK, "low UV with heavy overcast or smog"),
        (VibemonTypeT.GHOST, "fog or low visibility under low-UV conditions"),
        (VibemonTypeT.BUG, "humid tropical heat"),
        (VibemonTypeT.ROCK, "elevation or hail events"),
        (VibemonTypeT.DRAGON, "convective instability (CAPE)"),
        (VibemonTypeT.ELECTRIC, "thunderstorms"),
    ]

    requirements = (catalog.GEOLOCATION_REQUIREMENT,)
    data_sources = (
        catalog.DataSourceInfo(
            name="Open-Meteo",
            description="Daily forecast and air-quality series at trainer coordinates.",
        ),
    )

    payload_type = climate_schema.ClimatePayload

    def __init__(self) -> None:
        self.client = openmeteo_api.OpenMeteoClient()

    # ── INTERNAL HELPERS ──────────────────────────────────────────────────────────────

    def derive_signals(self, payload: climate_schema.ClimatePayload) -> dict[str, Signal]:
        """Create a mapping of Signals from the raw payload data."""
        CLIMATE_DEFAULTS: dict[str, float] = {
            "cape_mean": 100.0,
            "cloud_cover_mean": 60.0,
            "dew_point_2m_mean": 10.0,
            "dust_mean": 15.0,
            "et0_fao_evapotranspiration": 3.5,
            "pm2_5_mean": 25.0,
            "precipitation_sum": 1.5,
            "relative_humidity_2m_mean": 65.0,
            "shortwave_radiation_sum": 15.0,
            "snowfall_sum": 0.1,
            "temperature_2m_max": 20.0,
            "temperature_2m_min": 8.0,
            "uv_index_max": 6.0,
            "visibility_mean": 15000.0,
            "wind_gusts_10m_max": 30.0,
            "wind_speed_10m_max": 15.0,
        }

        d = payload.weather_augmented
        s = d["daily"]
        i = -1

        raws = {attr: CLIMATE_DEFAULTS[attr] if s[attr][i] is None else s[attr][i] for attr in CLIMATE_DEFAULTS}

        # fmt: off
        # ruff: noqa: E501
        return {
            sig.name: sig
            for sig in (
                Signal(name="cape_m", attr="cape_mean",                  raw=raws["cape_mean"],                  min=   0.00, med=   100.00, max=  5000.00),
                Signal(name="clouds", attr="cloud_cover_mean",           raw=raws["cloud_cover_mean"],           min=   0.00, med=    60.00, max=   100.00),
                Signal(name="dew_pt", attr="dew_point_2m_mean",          raw=raws["dew_point_2m_mean"],          min= -60.00, med=    10.00, max=    32.00),
                Signal(name="dust_m", attr="dust_mean",                  raw=raws["dust_mean"],                  min=   0.00, med=    15.00, max=  1000.00),
                Signal(name="elevat", attr="elevation",                  raw=d["elevation"],                     min=-430.00, med=   350.00, max=  5100.00),
                Signal(name="transp", attr="et0_fao_evapotranspiration", raw=raws["et0_fao_evapotranspiration"], min=   0.00, med=     3.50, max=    15.00),
                Signal(name="pollut", attr="pm2_5_mean",                 raw=raws["pm2_5_mean"],                 min=   0.00, med=    25.00, max=   500.00),
                Signal(name="precip", attr="precipitation_sum",          raw=raws["precipitation_sum"],          min=   0.00, med=     1.50, max=   500.00),
                Signal(name="humdty", attr="relative_humidity_2m_mean",  raw=raws["relative_humidity_2m_mean"],  min=   5.00, med=    65.00, max=   100.00),
                Signal(name="radiat", attr="shortwave_radiation_sum",    raw=raws["shortwave_radiation_sum"],    min=   0.00, med=    15.00, max=    35.00),
                Signal(name="snowfl", attr="snowfall_sum",               raw=raws["snowfall_sum"],               min=   0.00, med=     0.10, max=   100.00),
                Signal(name="tmp_hi", attr="temperature_2m_max",         raw=raws["temperature_2m_max"],         min= -40.00, med=    20.00, max=    55.00),
                Signal(name="tmp_lo", attr="temperature_2m_min",         raw=raws["temperature_2m_min"],         min= -60.00, med=     8.00, max=    35.00),
                Signal(name="uv_idx", attr="uv_index_max",               raw=raws["uv_index_max"],               min=   0.00, med=     6.00, max=    18.00),
                Signal(name="visibl", attr="visibility_mean",            raw=raws["visibility_mean"],            min=   0.00, med= 15000.00, max= 40000.00),
                Signal(name="windgu", attr="wind_gusts_10m_max",         raw=raws["wind_gusts_10m_max"],         min=   0.00, med=    30.00, max=   250.00),
                Signal(name="windsp", attr="wind_speed_10m_max",         raw=raws["wind_speed_10m_max"],         min=   0.00, med=    15.00, max=   150.00),
            )
        }
        # fmt: on

    def balance_for_bst(self, signals: dict[str, Signal]) -> providers_schema.BaseStatCenters:
        """Mix Signals to provide a stat profile."""
        obscurity = clamp(1.0 - signals["visibl"].center, minimum=0.0, maximum=1.0)

        return providers_schema.BaseStatCenters(
            hp=Signal.mix(signals["tmp_hi"] * 0.5, signals["tmp_lo"] * 0.5, mode="center"),
            attack=signals["windgu"].center,
            defense=clamp(0.65 * obscurity + 0.35 * signals["pollut"].center, minimum=0.0, maximum=1.0),
            sp_attack=Signal.mix(signals["radiat"] * 0.5, signals["cape_m"] * 0.5, mode="center"),
            sp_defense=Signal.mix(signals["humdty"] * 0.5, signals["precip"] * 0.5, mode="center"),
            speed=signals["windsp"].center,
        )

    # ── CORE PROTOCOL MEMBERS ─────────────────────────────────────────────────────────

    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> climate_schema.ClimatePayload:
        """Fetch and enrich climate payloads for a birth seed."""
        end_date = seed.datestamp
        start_date = seed.datestamp - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        async with asyncio.TaskGroup() as g:
            opts = {
                "latitude": seed.geo_coords[0],
                "longitude": seed.geo_coords[1],
                "start_date": start_date,
                "end_date": end_date,
            }

            wr_task = g.create_task(self.client.forecast(**opts))
            ar_task = g.create_task(self.client.air_quality(**opts))

        wr = wr_task.result()
        ar = ar_task.result()

        wr.raise_for_status()
        ar.raise_for_status()

        forecast = openmeteo_schema.ForecastResponse.model_validate(wr.json())
        air_quality = openmeteo_schema.AirQualityResponse.model_validate(ar.json())

        def daily_means(times: list[str], values: list[float | None]) -> dict[str, float]:
            return {
                day: statistics.fmean(day_values)
                for day, group in it.groupby(zip(times, values, strict=True), key=lambda tp: tp[0][:10])
                if (day_values := [value for _, value in group if value is not None])
            }

        pm25_by_day = daily_means(air_quality.hourly.time, air_quality.hourly.pm2_5)
        dust_by_day = daily_means(air_quality.hourly.time, air_quality.hourly.dust)

        # Inject hourly-derived aggregates onto the daily weather frame so replay is deterministic.
        daily = forecast.daily.model_dump()
        daily["pm2_5_mean"] = [pm25_by_day.get(day, 0.0) for day in daily["time"]]
        daily["dust_mean"] = [dust_by_day.get(day, 0.0) for day in daily["time"]]

        weather_augmented = forecast.model_dump()
        weather_augmented["daily"] = daily

        return climate_schema.ClimatePayload(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            weather_augmented=weather_augmented,
        )

    async def synthesize(self, seed: BirthSeed, payload: climate_schema.ClimatePayload) -> Affinity:
        """Translate captured climate payload to Affinity components."""
        rng = seed.rng(f"provider.{self.name}.moves")

        d = payload.weather_augmented
        s = d["daily"]
        i = -1

        # RAW DATA
        wmo_code = WeatherCode(s["weather_code"][i])
        signals = self.derive_signals(payload)

        # RANKED ELEMENTS BASED ON THE DATA
        rankings = self.determine_element_scores(signals=signals, weather_code=wmo_code)
        elements = filter_element_types(rankings)

        # BALANCE SIGNAL DATA FOR BASE STAT TRANSLATION
        normalized = self.balance_for_bst(signals)
        base_stats = normalized.scaled(elements=elements)

        # LOAD MOVES
        all_moves = self.selectable_moves()

        affinity = Affinity(
            identity=Identity(name="__", elements=elements, base=base_stats),
            visual_notes=self.visual_notes(weather_code=wmo_code, signals=signals),
            intensity=self.calculate_intensity(s, index=i),
            provider_id=self.name,
            element_rankings=rankings,
            moves=pick_starter_moves(moves=all_moves, rankings=rankings, elements=elements, k=10, rng=rng),
        )

        return affinity

    # ── PROTOCOL HELPERS ──────────────────────────────────────────────────────────────

    def visual_notes(
        self,
        *,
        weather_code: WeatherCode,
        signals: dict[str, Signal],
    ) -> str:
        """Summarize hatch-day weather as short creature-facing visual cues."""
        parts = [weather_code.visual_note]
        if accent := self._signal_accent(signals, weather_code):
            parts.append(accent)
        return "; ".join(parts)

    @staticmethod
    def _signal_accent(signals: dict[str, Signal], weather_code: WeatherCode) -> str | None:
        """Return one optional accent from the strongest qualifying continuous signal."""
        rules: tuple[tuple[str, float, frozenset[WeatherCode]], ...] = (
            ("pollut", 0.62, frozenset()),
            ("dust_m", 0.62, frozenset()),
            ("windsp", 0.72, _WINDY_WEATHER_CODES),
            ("elevat", 0.72, _SNOW_WEATHER_CODES),
            ("cape_m", 0.68, _STORM_WEATHER_CODES),
        )

        best_score = 0.0
        best_phrase: str | None = None
        for signal_name, threshold, skip_codes in rules:
            if weather_code in skip_codes:
                continue
            score = signals[signal_name].center
            if score < threshold or score <= best_score:
                continue
            best_score = score
            best_phrase = {
                "pollut": "soot-dulled markings",
                "dust_m": "grit-streaked hide",
                "windsp": "wind-raked fringe",
                "elevat": "alpine-bleached coat",
                "cape_m": "charged air bristling along the crest",
            }[signal_name]

        return best_phrase

    def calculate_intensity(self, daily: dict[str, list[float | None]], *, index: int) -> float:
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
        temp_max = [v or 20.0 for v in daily["temperature_2m_max"]]
        temp_min = [v or 8.0 for v in daily["temperature_2m_min"]]
        precip = [v or 1.5 for v in daily["precipitation_sum"]]
        wind_gusts = [v or 30.0 for v in daily["wind_gusts_10m_max"]]
        cape = [v or 100.0 for v in daily["cape_mean"]]

        # Visibility inverted: low visibility (fog/storms) = high intensity
        visibility_inverted = [50.0 - (v or 15000.0) for v in daily["visibility_mean"]]

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

        # FIRE — volcanic, dry deserts, hot springs.
        # Heat spine; radiation and heat-on-arid (desert) are alternate triggers.
        solar_radiation_score = signals["radiat"].ramp("N", thresh=0.65, reach=0.35)
        heat_temperature_score = signals["tmp_hi"].ramp("R", thresh=28.0, reach=20.0)
        fire_arid_factor = signals["humdty"].ramp("R", thresh=40.0, reach=30.0, invert=True)
        score[VibemonTypeT.FIRE] += max(
            solar_radiation_score, heat_temperature_score, heat_temperature_score * fire_arid_factor
        )

        # WATER — oceans, lakes, rivers, beaches, harbors.
        # Open-Meteo has no proximity-to-water field, so coastal/lakeside cannot be detected.
        # Falls back to direct precipitation only — known semantic gap.
        score[VibemonTypeT.WATER] += signals["precip"].ramp("R", thresh=0.5, reach=20.0)

        # GRASS — forests, meadows, parks, gardens.
        # Active transpiration or humid air — hydrated growing environment.
        plant_evapotrans_score = signals["transp"].ramp("N", thresh=0.30, reach=0.70)
        humid_saturation_score = signals["dew_pt"].ramp("N", thresh=0.75, reach=0.25)
        score[VibemonTypeT.GRASS] += max(plant_evapotrans_score, humid_saturation_score)

        # ICE — glaciers, snowy mountains, frozen caves.
        # Cold OR snow alone qualifies; elevation amplifies the mountain-ice profile.
        cold_temp_score = signals["tmp_lo"].ramp("R", thresh=0.0, reach=30.0, invert=True)
        snowfall_score = signals["snowfl"].ramp("R", thresh=0.5, reach=9.5)
        high_alt_factor = 1.0 + 0.5 * signals["elevat"].ramp("R", thresh=2000.0, reach=3000.0)
        score[VibemonTypeT.ICE] += min(1.0, max(cold_temp_score, snowfall_score) * high_alt_factor)

        # FLYING — high-altitude peaks, trees, open skies.
        # Wind is core; elevation and clear sky compound the sky-domain feel.
        wind_score = signals["windsp"].ramp("R", thresh=13.0, reach=40.0)
        altitude_factor = 1.0 + 0.5 * signals["elevat"].ramp("R", thresh=800.0, reach=2000.0)
        clear_sky_factor = 1.0 - 0.3 * signals["clouds"].ramp("N", thresh=0.70, reach=0.30)
        score[VibemonTypeT.FLYING] += min(1.0, wind_score * altitude_factor * clear_sky_factor)

        # FIGHTING — violent kinetic weather, not ordinary wind.
        # Gust excess separates sudden impact force from FLYING's sustained wind profile.
        gust_score = signals["windgu"].ramp("R", thresh=50.0, reach=70.0)
        gust_excess = max(0.0, signals["windgu"].raw - signals["windsp"].raw)
        gust_spike_score = clamp(gust_excess / 45.0, minimum=0.0, maximum=1.0)
        abrasive_air_score = signals["dust_m"].ramp("R", thresh=25.0, reach=150.0)
        low_visibility_impact = signals["visibl"].ramp("R", thresh=9000.0, reach=7000.0, invert=True)
        heavy_precip_impact = signals["precip"].ramp("R", thresh=20.0, reach=40.0)
        impact_score = max(abrasive_air_score, low_visibility_impact, heavy_precip_impact)
        score[VibemonTypeT.FIGHTING] += math.sqrt(gust_score * gust_spike_score * impact_score)

        # POISON — swamps, marshes, industrial zones, sewers.
        # Sole owner of pollution signal. Alt path: stagnant warm wetland (swamp).
        pollution_score = signals["pollut"].ramp("N", thresh=0.12, reach=0.95)
        swamp_humidity = signals["humdty"].ramp("R", thresh=75.0, reach=25.0)
        swamp_warmth = signals["tmp_hi"].ramp("R", thresh=22.0, reach=15.0)
        still_air_factor = signals["windsp"].ramp("R", thresh=8.0, reach=10.0, invert=True)
        swamp_score = swamp_humidity * swamp_warmth * still_air_factor
        score[VibemonTypeT.POISON] += max(pollution_score, swamp_score)

        # GROUND — deserts, dust flats, exposed dry earth.
        dust_score = signals["dust_m"].ramp("R", thresh=25.0, reach=150.0)
        dry_weather_gate = 1.0 - signals["precip"].ramp("R", thresh=1.0, reach=9.0)
        ground_arid_factor = signals["humdty"].ramp("R", thresh=70.0, reach=45.0, invert=True)
        exposed_ground_score = 0.60 * dry_weather_gate * ground_arid_factor
        score[VibemonTypeT.GROUND] += max(dust_score, exposed_ground_score)

        # BUG — woods, tall grass, farm land.
        # Warm humid air OR active crop transpiration — heat required, distinct from GRASS dew paths.
        tropical_humid = signals["humdty"].ramp("R", thresh=62.0, reach=25.0) * signals["tmp_hi"].ramp(
            "R", thresh=21.0, reach=15.0
        )
        farm_buzz = signals["transp"].ramp("N", thresh=0.30, reach=0.50) * signals["tmp_hi"].ramp(
            "R", thresh=18.0, reach=14.0
        )
        score[VibemonTypeT.BUG] += max(tropical_humid, farm_buzz)

        # ROCK — caves, mountains, cliffsides, mines.
        # Elevated exposed stone; cold or snowy days defer to ICE instead.
        elevation_score = signals["elevat"].ramp("R", thresh=400.0, reach=2400.0)
        cold_rock_veto = max(
            signals["tmp_lo"].ramp("R", thresh=5.0, reach=25.0, invert=True),
            signals["snowfl"].ramp("R", thresh=0.1, reach=1.5),
        )
        score[VibemonTypeT.ROCK] += min(1.0, elevation_score * (1.0 - cold_rock_veto))

        # GHOST — graveyards, abandoned buildings, fog-bound alleys.
        # Low visibility under low UV from gloomy weather; cold still air seals it.
        visibility_score = signals["visibl"].ramp("R", thresh=10.0, reach=6.0, invert=True)
        low_light_factor = 1.0 - 0.5 * signals["uv_idx"].ramp("N", thresh=0.30, reach=0.65)
        chill_factor = 1.0 + 0.3 * signals["tmp_lo"].ramp("R", thresh=10.0, reach=15.0, invert=True)
        score[VibemonTypeT.GHOST] += min(1.0, visibility_score * low_light_factor * chill_factor)

        # DRAGON — legendary shrines, deep craters, high summits.
        # Mythic combo: severe atmospheric instability AND extreme altitude. Multiplicative
        # so neither a calm peak nor a lowland storm alone qualifies — must be both.
        cape_score = signals["cape_m"].ramp("N", thresh=0.30, reach=0.70)
        altitude_score = signals["elevat"].ramp("R", thresh=2000.0, reach=3000.0)
        score[VibemonTypeT.DRAGON] += math.sqrt(cape_score * altitude_score)

        # ELECTRIC — power plants, urban centers, stormy plains.
        # Storms (CAPE) only — urban-grid path dropped to keep pollution exclusive to POISON.
        score[VibemonTypeT.ELECTRIC] += signals["cape_m"].ramp("N", thresh=0.35, reach=0.65)

        # DARK — shadowy overcast, smog, and heavy-cloud weather.
        # At least two of three: low UV, heavy overcast, urban smog.
        # Pairwise sqrt — single-signal cities (just cloudy, just smoggy) no longer qualify.
        low_uv_score = signals["uv_idx"].ramp("N", thresh=0.26, reach=0.30, invert=True)
        overcast_score = signals["clouds"].ramp("N", thresh=0.80, reach=0.20)
        smog_score = signals["pollut"].ramp("N", thresh=0.15, reach=0.30)
        score[VibemonTypeT.DARK] += max(
            math.sqrt(low_uv_score * overcast_score),
            math.sqrt(low_uv_score * smog_score),
            math.sqrt(overcast_score * smog_score),
        )

        # FAIRY — flower beds, enchanted forests, lakesides.
        # Bright clean sun OR humid sunlit haze; smog vetoes both paths.
        clean_air = 1.0 - signals["pollut"].ramp("N", thresh=0.05, reach=0.20)
        clear_sun = signals["uv_idx"].ramp("N", thresh=0.38, reach=0.52)
        misty_sun = signals["uv_idx"].ramp("N", thresh=0.28, reach=0.45) * signals["humdty"].ramp(
            "R", thresh=55.0, reach=30.0
        )
        score[VibemonTypeT.FAIRY] += clean_air * max(clear_sun, misty_sun)

        # NORMAL — fields, suburbs, residential baseline.
        # The "average day" is the absence of extremes, not a positive signal. Attentuated
        # at 0.3x so a moderate continuous signal (~0.25) competes evenly instead of being
        # buried by NORMAL at ~0.75. Still acts as safety net when nothing fires.
        score[VibemonTypeT.NORMAL] += 0.3 * (1.0 - max(score.values(), default=0.0))

        # General Tier structure:
        # - 0.5: RARE
        # - 0.3: MODERATE
        # - 0.4: HEAVY
        # - 0.2: LIGHT
        match weather_code:
            # Clear skies: unobstructed sun confirms high UV for FAIRY's continuous
            # block. FAIRY's clean_air gate prevents false positives in smoggy areas.
            case WeatherCode.CLEAR_SKY | WeatherCode.MAINLY_CLEAR:
                score[VibemonTypeT.FAIRY] += 0.2

            # Partly cloudy: shifting cloud cover and breezy air confirm FLYING's
            # wind-based continuous signal. Offsets the cloud-cover penalty that
            # FLYING's clear_sky_factor applies to its own score.
            case WeatherCode.PARTLY_CLOUDY:
                score[VibemonTypeT.FLYING] += 0.15

            # Heavy overcast confirms dark, cloudy conditions.
            case WeatherCode.OVERCAST:
                score[VibemonTypeT.NORMAL] += 0.3
                score[VibemonTypeT.DARK] += 0.2

            # All thunderstorm variants confirm electrical activity (rare event).
            # DRAGON bonus dropped — DRAGON now requires sqrt(cape * altitude); a lowland
            # thunderstorm bypassing the altitude gate via WMO bonus violates that semantic.
            # Mountain thunderstorms still trigger DRAGON via continuous block.
            case WeatherCode.THUNDERSTORM | WeatherCode.THUNDERSTORM_WITHOUT_PRECIP | WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY:  # fmt: skip
                score[VibemonTypeT.ELECTRIC] += 0.5

            # Light hail: thunderstorm + frozen-pellet impact (split between ICE and ROCK).
            case WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL:
                score[VibemonTypeT.ELECTRIC] += 0.5
                score[VibemonTypeT.ICE] += 0.2
                score[VibemonTypeT.ROCK] += 0.2

            # Heavy hail: thunderstorm + heavy frozen-pellet impact.
            case WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL:
                score[VibemonTypeT.ELECTRIC] += 0.5
                score[VibemonTypeT.ICE] += 0.3
                score[VibemonTypeT.ROCK] += 0.3
                score[VibemonTypeT.FIGHTING] += 0.2

            # Fog/rime confirm spectral conditions (rare event)
            case WeatherCode.FOG | WeatherCode.DEPOSITING_RIME_FOG:
                score[VibemonTypeT.GHOST] += 0.5

            # Light precipitation: drizzle + slight rain (common, weak signal)
            case WeatherCode.DRIZZLE_LIGHT | WeatherCode.DRIZZLE_MODERATE | WeatherCode.RAIN_SLIGHT | WeatherCode.RAIN_SHOWERS_SLIGHT:  # fmt: skip
                score[VibemonTypeT.WATER] += 0.3

            # Moderate precipitation (common, medium signal)
            case WeatherCode.DRIZZLE_DENSE | WeatherCode.RAIN_MODERATE | WeatherCode.RAIN_SHOWERS_MODERATE:
                score[VibemonTypeT.WATER] += 0.4

            # Heavy precipitation
            case WeatherCode.RAIN_HEAVY:
                score[VibemonTypeT.WATER] += 0.5

            # Heavy precipitation (intense, strong signal)
            case WeatherCode.RAIN_SHOWERS_VIOLENT:
                score[VibemonTypeT.WATER] += 0.5
                score[VibemonTypeT.FIGHTING] += 0.2

            # Freezing rain/drizzle split affinity between water (liquid) and ice (freezing)
            case WeatherCode.FREEZING_RAIN_LIGHT | WeatherCode.FREEZING_DRIZZLE_LIGHT | WeatherCode.FREEZING_DRIZZLE_DENSE:  # fmt: skip
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
                score[VibemonTypeT.FIGHTING] += 0.1

            case _:
                _LOGGER.warning("missing_mapped_weather_code", code=weather_code)

        return score
