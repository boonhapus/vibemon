from typing import Any, ClassVar
import collections
import datetime as dt
import functools as ft
import itertools as it
import math
import statistics

import niquests
import structlog

from app.core.math import clamp
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.strength_formulas import base_stat_asymmetric_scaling, stat_ratio_from_grade
from app.providers.base import VibeProvider
from app.providers.helpers import Signal, filter_element_types, pick_starter_moves

from . import api as _weather
from .const import WeatherCode

_LOGGER = structlog.get_logger(__name__)


class ClimateProvider(VibeProvider):
    """
    A Vibemon is born from the sky above its birthplace.

    Open-Meteo's daily forecast at the trainer's coordinates becomes genetic
    material, folding live weather signals into an `Affinity`.

    Six continuous signals route directly to base stats: temperature (HP),
    wind gusts (Attack), elevation (Defense), radiation (Sp. Attack),
    precipitation (Sp. Defense), and sustained wind (Speed).

    The result is that a creature born in a Death Valley heatwave has a
    fundamentally different soul than one from an Andean snowstorm or London
    fog—both stats and flavor emergent from the actual sky at birth.
    """

    name = "climate"

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "overcast skies without precipitation"),
        (VibemonTypeT.FIRE, "solar radiation or extreme heat"),
        (VibemonTypeT.WATER, "precipitation (rain, drizzle, freezing rain)"),
        (VibemonTypeT.GRASS, "evapotranspiration or humid dew points"),
        (VibemonTypeT.ICE, "sub-freezing temperatures or snowfall"),
        (VibemonTypeT.FLYING, "sustained winds (15+ km/h)"),
        (VibemonTypeT.FIGHTING, "violent gust spikes and impact weather"),
        (VibemonTypeT.GROUND, "mineral dust or dry exposed topsoil"),
        (VibemonTypeT.FAIRY, "UV radiation exposure"),
        (VibemonTypeT.POISON, "air pollution concentration"),
        (VibemonTypeT.DARK, "low visibility or heavy overcast"),
        (VibemonTypeT.GHOST, "fog or low visibility under low-UV conditions"),
        (VibemonTypeT.BUG, "humid tropical heat"),
        (VibemonTypeT.ROCK, "elevation or hail events"),
        (VibemonTypeT.DRAGON, "convective instability (CAPE)"),
        (VibemonTypeT.ELECTRIC, "thunderstorms"),
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

        # FIRE — volcanic, dry deserts, hot springs.
        # Heat spine; radiation and heat-on-arid (desert) are alternate triggers.
        solar_radiation_score = signals["radiat"].ramp("N", thresh=0.65, reach=0.35)
        heat_temperature_score = signals["tmp_hi"].ramp("R", thresh=32.0, reach=20.0)
        fire_arid_factor = signals["humdty"].ramp("R", thresh=40.0, reach=30.0, invert=True)
        score[VibemonTypeT.FIRE] += max(
            solar_radiation_score, heat_temperature_score, heat_temperature_score * fire_arid_factor
        )

        # WATER — oceans, lakes, rivers, beaches, harbors.
        # Open-Meteo has no proximity-to-water field, so coastal/lakeside cannot be detected.
        # Falls back to direct precipitation only — known semantic gap.
        score[VibemonTypeT.WATER] += signals["precip"].ramp("R", thresh=1.0, reach=49.0)

        # GRASS — forests, meadows, parks, gardens.
        # Active transpiration, humid air, OR moist topsoil — any one indicates a
        # hydrated growing environment.
        plant_evapotrans_score = signals["transp"].ramp("N", thresh=0.30, reach=0.70)
        humid_saturation_score = signals["dew_pt"].ramp("N", thresh=0.75, reach=0.25)
        moist_soil_score = signals["soilmt"].ramp("R", thresh=0.25, reach=0.25)
        score[VibemonTypeT.GRASS] += max(plant_evapotrans_score, humid_saturation_score, moist_soil_score)

        # ICE — glaciers, snowy mountains, frozen caves.
        # Cold OR snow alone qualifies; elevation amplifies the mountain-ice profile.
        cold_temp_score = signals["tmp_lo"].ramp("R", thresh=0.0, reach=30.0, invert=True)
        snowfall_score = signals["snowfl"].ramp("R", thresh=0.5, reach=9.5)
        high_alt_factor = 1.0 + 0.5 * signals["elevat"].ramp("R", thresh=2000.0, reach=3000.0)
        score[VibemonTypeT.ICE] += min(1.0, max(cold_temp_score, snowfall_score) * high_alt_factor)

        # FLYING — high-altitude peaks, trees, open skies.
        # Wind is core; elevation and clear sky compound the sky-domain feel.
        wind_score = signals["windsp"].ramp("R", thresh=10.0, reach=40.0)
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
        # Keep GROUND tied to mineral dust and dry topsoil; wet mud belongs to WATER/GRASS ecology.
        dust_score = signals["dust_m"].ramp("R", thresh=25.0, reach=150.0)
        dry_topsoil_score = signals["soilmt"].ramp("R", thresh=0.14, reach=0.14, invert=True)
        dry_weather_gate = 1.0 - signals["precip"].ramp("R", thresh=1.0, reach=9.0)
        exposed_ground_score = dry_topsoil_score * dry_weather_gate
        score[VibemonTypeT.GROUND] += max(dust_score, exposed_ground_score)

        # BUG — woods, tall grass, farm land.
        # Verdant warm humidity AND moist soil — all three required. Cube root preserves
        # multiplicative gating without crushing legitimate forest/farm conditions.
        humid_stress_factor = signals["humdty"].ramp("R", thresh=70.0, reach=30.0)
        heat_stress_factor = signals["tmp_hi"].ramp("R", thresh=25.0, reach=25.0)
        farm_soil_factor = signals["soilmt"].ramp("R", thresh=0.20, reach=0.30)
        score[VibemonTypeT.BUG] += (humid_stress_factor * heat_stress_factor * farm_soil_factor) ** (1 / 3)

        # ROCK — caves, mountains, cliffsides, mines.
        # Elevation primary; arid air sharpens exposed-stone profile (vs. lush mountain).
        elevation_score = signals["elevat"].ramp("R", thresh=600.0, reach=4500.0)
        arid_rock_factor = 1.0 + 0.3 * signals["humdty"].ramp("R", thresh=50.0, reach=40.0, invert=True)
        score[VibemonTypeT.ROCK] += min(1.0, elevation_score * arid_rock_factor)

        # GHOST — graveyards, abandoned buildings, dark alleys.
        # Fog/low visibility under low UV (dawn/dusk/overcast); cold still air seals it.
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

        # DARK — shadows, cemeteries, urban areas at night.
        # At least two of three: low UV (shadow/night), heavy overcast, urban smog.
        # Pairwise sqrt — single-signal cities (just cloudy, just smoggy) no longer qualify.
        low_uv_score = signals["uv_idx"].ramp("N", thresh=0.30, reach=0.30, invert=True)
        overcast_score = signals["clouds"].ramp("N", thresh=0.75, reach=0.25)
        smog_score = signals["pollut"].ramp("N", thresh=0.15, reach=0.30)
        score[VibemonTypeT.DARK] += max(
            math.sqrt(low_uv_score * overcast_score),
            math.sqrt(low_uv_score * smog_score),
            math.sqrt(overcast_score * smog_score),
        )

        # FAIRY — flower beds, enchanted forests, lakesides.
        # Pristine sun on damp clean air: UV * clean_air * humidity. Multiplicative —
        # smog or dryness vetoes the enchanted feel.
        uv_score = signals["uv_idx"].ramp("N", thresh=0.30, reach=0.65)
        clean_air_factor = 1.0 - signals["pollut"].ramp("N", thresh=0.05, reach=0.20)
        moisture_factor = 0.5 + 0.5 * signals["humdty"].ramp("R", thresh=50.0, reach=30.0)
        score[VibemonTypeT.FAIRY] += uv_score * clean_air_factor * moisture_factor

        # NORMAL — fields, suburbs, residential baseline.
        # The "average day" is the absence of extremes, not a positive signal. Attentuated
        # at 0.3x so a moderate continuous signal (~0.25) competes evenly instead of being
        # buried by NORMAL at ~0.75. Still acts as safety net when nothing fires.
        score[VibemonTypeT.NORMAL] += 0.3 * (1.0 - max(score.values(), default=0.0))  # maybe 0.4

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
                score[VibemonTypeT.FLYING] += 0.2

            # Heavy overcast confirms dark, cloudy conditions.
            # DARK bonus raised 0.2 → 0.3 to compensate for stricter 2-of-3 continuous gate
            # (pure overcast no longer fires DARK from continuous signals alone).
            case WeatherCode.OVERCAST:
                score[VibemonTypeT.NORMAL] += 0.3
                score[VibemonTypeT.DARK] += 0.3

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

    async def fetch(self, seed: BirthSeed) -> dict[str, Any]:
        """Fetch and enrich climate payloads for a birth seed."""
        end_date = seed.datestamp
        start_date = seed.datestamp - dt.timedelta(days=1) - dt.timedelta(weeks=6)

        try:
            # TODO: use asyncio.gather when upgraded to paid OpenMeteo.
            wr = await self.client.current_weather(
                latitude=seed.geo_coords[0],
                longitude=seed.geo_coords[1],
                start_date=start_date,
                end_date=end_date,
            )
            ar = await self.client.air_quality(
                latitude=seed.geo_coords[0],
                longitude=seed.geo_coords[1],
                start_date=start_date,
                end_date=end_date,
            )

            wr.raise_for_status()
            ar.raise_for_status()
        except niquests.HTTPError as e:
            self._log_http_error(e)
            raise

        d = wr.json()
        a = ar.json()
        s = d["daily"]

        def daily_means(times: list[str], values: list[float | None]) -> dict[str, float]:
            return {
                day: statistics.fmean(day_values)
                for day, group in it.groupby(zip(times, values, strict=True), key=lambda tp: tp[0][:10])
                if (day_values := [value for _, value in group if value is not None])
            }

        pm25_by_day = daily_means(a["hourly"]["time"], a["hourly"]["pm2_5"])
        dust_by_day = daily_means(a["hourly"]["time"], a["hourly"]["dust"])
        soil_moisture_by_day = daily_means(d["hourly"]["time"], d["hourly"]["soil_moisture_0_to_1cm"])

        # Inject hourly-derived aggregates onto the daily weather frame so replay is deterministic.
        s["pm2_5_mean"] = [pm25_by_day.get(day, 0.0) for day in s["time"]]
        s["dust_mean"] = [dust_by_day.get(day, 0.0) for day in s["time"]]
        s["soil_moisture_0_to_1cm_mean"] = [soil_moisture_by_day.get(day, 0.18) for day in s["time"]]

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "weather_augmented": d,
        }

    async def synthesize(self, seed: BirthSeed, payload: dict[str, Any]) -> Affinity:
        """Translate captured climate payload to Affinity components."""
        rng = seed.rng(f"provider.{self.name}.moves")

        d = payload["weather_augmented"]
        s = d["daily"]
        i = -1

        # fmt: off
        # ruff: noqa: E501
        signals = {
            sig.name: sig
            for sig in (
                # THESE ARE GLOBAL, INHABITED (MIN, MED, MAX) RANGES FOR EACH ATTRIBUTE.
                Signal(name="cape_m", attr="cape_mean",                  raw=s["cape_mean"][i],                   min=   0.00, med=   100.00, max=  5000.00),
                Signal(name="clouds", attr="cloud_cover_mean",           raw=s["cloud_cover_mean"][i],            min=   0.00, med=    60.00, max=   100.00),
                Signal(name="dew_pt", attr="dew_point_2m_mean",          raw=s["dew_point_2m_mean"][i],           min= -60.00, med=    10.00, max=    32.00),
                Signal(name="dust_m", attr="dust_mean",                  raw=s["dust_mean"][i],                   min=   0.00, med=    15.00, max=  1000.00),
                Signal(name="elevat", attr="elevation",                  raw=d["elevation"],                      min=-430.00, med=   350.00, max=  5100.00),
                Signal(name="transp", attr="et0_fao_evapotranspiration", raw=s["et0_fao_evapotranspiration"][i],  min=   0.00, med=     3.50, max=    15.00),
                Signal(name="pollut", attr="pm2_5_mean",                 raw=s["pm2_5_mean"][i],                  min=   0.00, med=    25.00, max=   500.00),
                Signal(name="precip", attr="precipitation_sum",          raw=s["precipitation_sum"][i],           min=   0.00, med=     1.50, max=   500.00),
                Signal(name="pressr", attr="pressure_msl_mean",          raw=s["pressure_msl_mean"][i],           min= 970.00, med=  1013.20, max=  1050.00),
                Signal(name="humdty", attr="relative_humidity_2m_mean",  raw=s["relative_humidity_2m_mean"][i],   min=   5.00, med=    65.00, max=   100.00),
                Signal(name="radiat", attr="shortwave_radiation_sum",    raw=s["shortwave_radiation_sum"][i],     min=   0.00, med=    15.00, max=    35.00),
                Signal(name="snowfl", attr="snowfall_sum",               raw=s["snowfall_sum"][i],                min=   0.00, med=     0.10, max=   100.00),
                Signal(name="soilmt", attr="soil_moisture_0_to_1cm_mean",raw=s["soil_moisture_0_to_1cm_mean"][i], min=   0.00, med=     0.25, max=     0.55),
                Signal(name="tmp_hi", attr="temperature_2m_max",         raw=s["temperature_2m_max"][i],          min= -40.00, med=    20.00, max=    55.00),
                Signal(name="tmp_lo", attr="temperature_2m_min",         raw=s["temperature_2m_min"][i],          min= -60.00, med=     8.00, max=    35.00),
                Signal(name="uv_idx", attr="uv_index_max",               raw=s["uv_index_max"][i],                min=   0.00, med=     6.00, max=    18.00),
                Signal(name="visibl", attr="visibility_mean",            raw=s["visibility_mean"][i],             min=   0.00, med= 15000.00, max= 40000.00),
                Signal(name="windgu", attr="wind_gusts_10m_max",         raw=s["wind_gusts_10m_max"][i],          min=   0.00, med=    30.00, max=   250.00),
                Signal(name="windsp", attr="wind_speed_10m_max",         raw=s["wind_speed_10m_max"][i],          min=   0.00, med=    15.00, max=   150.00),
            )
        }
        # fmt: on

        wmo_code = WeatherCode(s["weather_code"][i])
        rankings = self.determine_element_scores(signals=signals, weather_code=wmo_code)
        elements = filter_element_types(rankings)

        # fmt: off
        hp_signal  = Signal.mix(signals["tmp_hi"] * 0.5, signals["elevat"] * 0.5, mode="center")  # mass + altitude endurance
        atk_signal = signals["windgu"].center                                                     # gust impact
        def_signal = Signal.mix(signals["elevat"] * 0.6, signals["pressr"] * 0.4, mode="center")  # solidity + compression
        spa_signal = Signal.mix(signals["radiat"] * 0.5, signals["cape_m"] * 0.5, mode="center")  # solar + electric flux
        spd_signal = Signal.mix(signals["humdty"] * 0.5, signals["precip"] * 0.5, mode="center")  # cushion + dampening
        spe_signal = signals["windsp"].center                                                     # kinetic
        # fmt: on

        ratio = ft.partial(stat_ratio_from_grade, elements=elements)

        affinity = Affinity(
            identity=Identity(
                name="__",
                elements=elements,
                base_hp=base_stat_asymmetric_scaling(ratio(hp_signal, stat="hp"), stat="hp"),
                base_attack=base_stat_asymmetric_scaling(ratio(atk_signal, stat="attack"), stat="attack"),
                base_defense=base_stat_asymmetric_scaling(ratio(def_signal, stat="defense"), stat="defense"),
                base_sp_attack=base_stat_asymmetric_scaling(ratio(spa_signal, stat="sp_attack"), stat="sp_attack"),
                base_sp_defense=base_stat_asymmetric_scaling(ratio(spd_signal, stat="sp_defense"), stat="sp_defense"),
                base_speed=base_stat_asymmetric_scaling(ratio(spe_signal, stat="speed"), stat="speed"),
            ),
            visual_notes=wmo_code.description,
            intensity=self.calculate_intensity(s, index=i),
            provider_id=self.name,
            moves=pick_starter_moves(
                moves=self.selectable_moves(), rankings=rankings, elements=elements, k=10, rng=rng
            ),
        )

        return affinity
