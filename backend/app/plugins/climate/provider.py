import collections
import functools as ft
import math
import random
import statistics

from app.balance.formulas import base_stat_asymmetric_scaling
from app.plugins.provider import VibeProvider
from app.plugins.helpers import Signal, filter_element_types
from app import schema, types, utils

from .const import WeatherCode
from . import _weather, moves


class ClimateProvider(VibeProvider):
    """
    A Vibemon is born from the sky above its birthplace.

    This provider treats live weather as genetic material: Open-Meteo's daily
    forecast at the trainer's coordinates is folded into a `schema.Affinity`.

    Each elemental type is seeded by the conditions that thematically suit it:

    - ICE      — sub-freezing temperature, snowfall, freezing precip, hail
    - FIRE     — heat above ~30 °C
    - DRAGON   — extreme heat above ~38 °C
    - WATER    — rain, drizzle
    - GRASS    — high dew point, humid air
    - POISON   — hot + humid stagnant air
    - BUG      — warm + humid + calm winds, light drizzle
    - FLYING   — wind and gusts, high elevation
    - ELECTRIC — UV index, shortwave radiation, thunderstorms
    - GROUND   — elevation, dry + windy abrasion
    - ROCK     — higher elevation, hail
    - GHOST    — reduced visibility, fog
    - DARK     — severe obscurity
    - STEEL    — arid + windy air with intense radiation
    - FAIRY    — mild, gentle, bright, comfortably humid weather
    - PSYCHIC  — clear, bright, calm air
    - FIGHTING — gust/spread strain, thermal stress, thunderstorms

    Six signals are routed straight into the base stats, so the creature's
    body literally reflects the sky: temperature spread becomes HP, gusts
    become Attack, elevation becomes Defense, radiation becomes Sp. Attack,
    humidity becomes Sp. Defense, and sustained wind becomes Speed.

    The result is that a creature caught during a Death Valley heatwave will
    have a genuinely different soul than one caught in an Andean snowstorm or
    a London fog, with both stats and flavor traceable back to the actual
    weather that produced it.
    """

    name = "climate"

    def __init__(self) -> None:
        self.client = _weather.OpenMeteoAPIClient()

    def calculate_intensity(self, daily: dict[str, list[float]], *, index: int) -> float:
        """
        Calculates a normalized weather intensity score (0.0 to 1.0) for a specific day.

        Computes Z-scores to identify the most extreme outlier. The maximum absolute
        deviation is passed through a sigmoid function, where 0.5 represents an average
        day, values > 0.5 indicate high intensity, and values < 0.5 indicate unusually
        low intensity.
        """
        keys = (
            "apparent_temperature_mean",
            "wind_gusts_10m_max",
            "relative_humidity_2m_mean",
            "shortwave_radiation_sum",
        )

        def z_score(values: list[float]) -> float:
            if len(values) < 2 or not (stdev := statistics.stdev(values)):
                return 0.0
            return (values[index] - statistics.mean(values)) / stdev

        # Degenerate inputs collapse to z=0, which sigmoids cleanly to 0.5.
        deviation = max((z_score(daily[k]) for k in keys), key=abs, default=0.0)
        return round(1.0 / (1.0 + math.exp(-deviation)), 4)

    def determine_element_scores(
        self,
        signals: dict[str, Signal],
        weather_code: WeatherCode | None = None,
    ) -> dict[types.VibemonTypeT, float]:
        scores: collections.defaultdict[types.VibemonTypeT, float] = collections.defaultdict(float)

        clamp = ft.partial(utils.clamp, minimum=0, maximum=1)
        """Ensure the value stays within the unit interval."""

        def add(element: types.VibemonTypeT, value: float) -> None:
            """Raise the contribution of the element by value."""
            scores[element] += value

        temp = signals["temperature"]
        sprd = signals["spread"]
        rain = signals["rain"]
        snow = signals["snow"]
        humi = signals["humidity"]
        dewp = signals["dew_point"]
        wind = signals["wind_speed"]
        gust = signals["wind_gusts"]
        uvid = signals["uv_index"]
        rads = signals["radiation"]
        elev = signals["elevation"]
        visi = signals["visibility"]

        # Composite conditions reused across multiple element mappings.
        warm_humid = clamp((temp.raw - 18.0) / 12.0) * clamp((humi.normal - 0.55) / 0.45)
        calm_winds = clamp(1.0 - wind.normal * 1.25)
        arid_scour = clamp((0.40 - humi.normal) / 0.40) * max(wind.normal, gust.normal)
        mild_temps = clamp(1.0 - abs(temp.raw - 18.0) / 14.0)
        gentle_air = clamp(1.0 - max(wind.normal, gust.normal) * 1.15)
        bright_air = clamp((visi.normal - 0.65) / 0.35)
        clear_mind = clamp((visi.normal - 0.75) / 0.25)
        solar_glow = clamp((max(uvid.normal, rads.normal) - 0.50) / 0.50)
        calm_focus = clamp(1.0 - max(wind.normal, gust.normal))
        harsh_load = max(gust.normal, sprd.normal)
        temp_strss = max(clamp((temp.raw - 34.0) / 14.0), clamp((0.0 - temp.raw) / 18.0))

        # Sub-freezing temperatures map directly to cryo affinity.
        add(types.VibemonTypeT.ICE, clamp((0.0 - temp.raw) / 20.0) * 0.9)

        # Heat above ~30 C is where fire affinity begins ramping.
        add(types.VibemonTypeT.FIRE, clamp((temp.raw - 30.0) / 20.0))

        # Extreme heat gets a small "mythic intensity" dragon tail.
        add(types.VibemonTypeT.DRAGON, clamp((temp.raw - 38.0) / 10.0) * 0.35)

        # Rain is the most literal hydrologic signal.
        add(types.VibemonTypeT.WATER, rain.normal * 1.1)

        # Snowfall reinforces ice independently of ambient temperature.
        add(types.VibemonTypeT.ICE, snow.normal * 1.2)

        # Higher dew point indicates lush, moisture-rich air masses.
        add(types.VibemonTypeT.GRASS, clamp((dewp.raw - 10.0) / 20.0) * 0.8)

        # Humid air adds a softer vegetation bias.
        add(types.VibemonTypeT.GRASS, clamp((humi.normal - 0.55) / 0.45) * 0.4)

        # Hot + humid conditions model stagnant/oppressive "toxic" atmosphere.
        add(types.VibemonTypeT.POISON, clamp((humi.normal - 0.70) / 0.30) * clamp((temp.raw - 24.0) / 12.0) * 0.6)

        # Warm, humid, and calmer air weakly supports bugs.
        add(types.VibemonTypeT.BUG, warm_humid * calm_winds * 0.55)

        # Wind is the primary FLYING signal, with high-elevation secondary support.
        # Wind/gust strength is the primary aerial driver.
        add(types.VibemonTypeT.FLYING, max(wind.normal * 0.9, gust.normal * 0.75))

        # High elevation contributes a smaller exposed/thin-air flying component.
        add(types.VibemonTypeT.FLYING, clamp((elev.normal - 0.60) / 0.40) * 0.45)

        # UV acts as a direct energy proxy.
        add(types.VibemonTypeT.ELECTRIC, clamp((uvid.normal - 0.35) / 0.65) * 0.7)

        # Radiation reinforces electric as a secondary energy channel.
        add(types.VibemonTypeT.ELECTRIC, clamp((rads.normal - 0.45) / 0.55) * 0.45)

        # Elevation establishes baseline terrain/earth identity.
        add(types.VibemonTypeT.GROUND, elev.normal * 0.75)

        # Rocky identity rises in higher elevation bands.
        add(types.VibemonTypeT.ROCK, clamp((elev.normal - 0.35) / 0.65) * 0.9)

        # Dry + windy conditions nudge toward dust/erosion-style ground affinity.
        add(types.VibemonTypeT.GROUND, clamp((0.35 - humi.normal) / 0.35) * clamp((wind.normal - 0.40) / 0.60) * 0.5)

        # Reduced visibility yields uncanny/spectral atmosphere.
        add(types.VibemonTypeT.GHOST, clamp((0.60 - visi.normal) / 0.60))

        # Severe obscurity escalates toward dark affinity.
        add(types.VibemonTypeT.DARK, clamp((0.25 - visi.normal) / 0.25) * 0.9)

        # Harsh dry abrasion plus high radiation creates metallic/hard-edged feel.
        add(types.VibemonTypeT.STEEL, arid_scour * 0.55 + clamp((rads.normal - 0.75) / 0.25) * 0.2)

        # Comfortable, gentle, clear weather yields a soft fairy profile.
        add(types.VibemonTypeT.FAIRY, mild_temps * gentle_air * bright_air * clamp((humi.normal - 0.40) / 0.35) * 0.55)

        # Calm + clear + bright conditions represent focused/psychic atmosphere.
        add(types.VibemonTypeT.PSYCHIC, clear_mind * solar_glow * calm_focus * 0.65)

        # Climatic strain and thermal stress combine into endurance/fighting flavor.
        add(types.VibemonTypeT.FIGHTING, harsh_load * 0.45 + temp_strss * 0.25)

        match weather_code:
            # Amplify the types based on the severity of the WeatherCode.
            # Generally the more severe a code, the more it contributes to the
            # resulting unit interval.
            case WeatherCode.THUNDERSTORM_WITHOUT_PRECIP:
                add(types.VibemonTypeT.ELECTRIC, 0.55)
                add(types.VibemonTypeT.FIGHTING, 0.15)

            case WeatherCode.THUNDERSTORM:
                add(types.VibemonTypeT.ELECTRIC, 0.7)
                add(types.VibemonTypeT.FIGHTING, 0.2)

            case WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY:
                add(types.VibemonTypeT.ELECTRIC, 0.8)
                add(types.VibemonTypeT.FIGHTING, 0.3)

            case WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL:
                add(types.VibemonTypeT.ELECTRIC, 0.6)
                add(types.VibemonTypeT.ICE, 0.4)
                add(types.VibemonTypeT.ROCK, 0.3)

            case WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL:
                add(types.VibemonTypeT.ELECTRIC, 0.75)
                add(types.VibemonTypeT.ICE, 0.55)
                add(types.VibemonTypeT.ROCK, 0.45)

            case WeatherCode.FREEZING_DRIZZLE_LIGHT | WeatherCode.FREEZING_RAIN_LIGHT:
                add(types.VibemonTypeT.ICE, 0.45)
                add(types.VibemonTypeT.WATER, 0.2)

            case WeatherCode.FREEZING_DRIZZLE_DENSE | WeatherCode.FREEZING_RAIN_HEAVY:
                add(types.VibemonTypeT.ICE, 0.7)
                add(types.VibemonTypeT.WATER, 0.3)

            case WeatherCode.SNOW_FALL_SLIGHT | WeatherCode.SNOW_SHOWERS_SLIGHT | WeatherCode.SNOW_GRAINS:
                add(types.VibemonTypeT.ICE, 0.45)

            case WeatherCode.SNOW_FALL_MODERATE:
                add(types.VibemonTypeT.ICE, 0.65)

            case WeatherCode.SNOW_FALL_HEAVY | WeatherCode.SNOW_SHOWERS_HEAVY:
                add(types.VibemonTypeT.ICE, 0.8)

            case WeatherCode.RAIN_SLIGHT | WeatherCode.RAIN_SHOWERS_SLIGHT:
                add(types.VibemonTypeT.WATER, 0.4)

            case WeatherCode.RAIN_MODERATE | WeatherCode.RAIN_SHOWERS_MODERATE:
                add(types.VibemonTypeT.WATER, 0.6)

            case WeatherCode.RAIN_HEAVY | WeatherCode.RAIN_SHOWERS_VIOLENT:
                add(types.VibemonTypeT.WATER, 0.8)

            case WeatherCode.FOG | WeatherCode.DEPOSITING_RIME_FOG:
                add(types.VibemonTypeT.GHOST, 0.5)

            case WeatherCode.DRIZZLE_LIGHT:
                add(types.VibemonTypeT.WATER, 0.25)
                add(types.VibemonTypeT.BUG, 0.1)

            case WeatherCode.DRIZZLE_MODERATE:
                add(types.VibemonTypeT.WATER, 0.35)
                add(types.VibemonTypeT.BUG, 0.15)

            case WeatherCode.DRIZZLE_DENSE:
                add(types.VibemonTypeT.WATER, 0.5)
                add(types.VibemonTypeT.BUG, 0.2)

            case _:
                pass

        return scores

    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Translate raw API data to Affinity components."""
        # FETCH THE LAST 4 WEEKS OF DATA FOR A GEO.
        r = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        d = r.json()
        s = d["daily"]
        i = -1

        signals = {
            # temperature   (-30, 50) °C
            #     Mean daily air temperature. Lower bound captures sustained
            #     cold-climate winters (Yakutsk, interior Canada); colder readings
            #     exist but are rare for daily means. Upper bound captures the
            #     hottest daily means on record (Death Valley, Lut Desert);
            #     instantaneous extremes can exceed 55 °C but daily means do not.
            "temperature": Signal(attr="temperature_2m_mean", raw=s["temperature_2m_mean"][i], min=-30.0, max=50.0),

            # spread   (1, 20) °C
            #     Range of apparent_temperature_mean across the forecast window.
            #     Coastal/tropical climates: 1–3 °C. Continental deserts: 15–20 °C.
            "spread": Signal(attr="spread", raw=max(s["apparent_temperature_mean"]) - min(s["apparent_temperature_mean"]), min=1.0, max=20.0),

            # rain          (0, 50) mm/day
            #     Daily rainfall total. 50 mm/day represents a heavy-precipitation
            #     day across most national meteorological services. Tropical tail
            #     events can exceed this and intentionally saturate.
            "rain": Signal(attr="rain_sum", raw=s["rain_sum"][i], min=0.0, max=50.0),

            # snow          (0, 20) cm/day
            #     Daily snowfall. 20 cm/day is a significant snowfall event;
            #     U.S. NWS heavy-snow warnings typically trigger around 15 cm
            #     in 12 hours.
            "snow": Signal(attr="snowfall_sum", raw=s["snowfall_sum"][i], min=0.0, max=20.0),

            # humidity      (5, 95) %RH
            #     Relative humidity. Trims sub-5 % (extreme desert) and >95 %
            #     (near-saturation) tails to preserve resolution across the
            #     inhabited 20–80 % range.
            "humidity": Signal(attr="relative_humidity_2m_mean", raw=s["relative_humidity_2m_mean"][i], min=5.0, max=95.0),

            # dew_point     (-40, 35) °C
            #     Dew point. Upper bound is the highest reliably recorded dew point
            #     on Earth (Dhahran, Saudi Arabia, July 2003). Above 24 °C is
            #     classified as "oppressive." Lower bound captures extreme
            #     dry-cold winter conditions in continental interiors.
            "dew_point": Signal(attr="dew_point_2m_mean", raw=s["dew_point_2m_mean"][i], min=-40.0, max=35.0),

            # wind_speed    (3, 55) km/h
            #     Sustained wind. Lower bound is Beaufort 1 — below this, conditions
            #     are effectively calm. Upper bound is Beaufort 7–8 (near-gale to
            #     gale); higher sustained winds are storm conditions.
            "wind_speed": Signal(attr="wind_speed_10m_max", raw=s["wind_speed_10m_max"][i], min=3.0, max=55.0),

            # wind_gusts    (5, 90) km/h
            #     Peak gust speed. Gusts routinely exceed sustained winds; 90 km/h
            #     corresponds to Beaufort 10 (storm-force) and serves as a
            #     reasonable upper bound for non-hurricane events.
            "wind_gusts": Signal(attr="wind_gusts_10m_max", raw=s["wind_gusts_10m_max"][i], min=5.0, max=90.0),

            # uv_index      (0, 14)
            #     UV Index. WHO categorises 11+ as "extreme." Tropical high-altitude
            #     readings can exceed 15 but are unusual.
            "uv_index": Signal(attr="uv_index_max", raw=s["uv_index_max"][i], min=0.0, max=14.0),

            # radiation     (1, 32) MJ/m²
            #     Daily shortwave radiation sum. ~32 MJ/m² is the practical clear-sky
            #     summer maximum at low latitudes per measurement studies (BOM
            #     Australia, eastern Mediterranean).
            "radiation": Signal(attr="shortwave_radiation_sum", raw=s["shortwave_radiation_sum"][i], min=1.0, max=32.0),

            # elevation     (0, 3500) m
            #     Surface elevation. Sea level to roughly La Paz altitude — the
            #     highest major population center. Habitation above 3500 m exists
            #     (Andean villages, Tibetan plateau) but is rare.
            "elevation": Signal(attr="elevation", raw=d["elevation"], min=0.0, max=3500.0),

            # visibility    (0, 100000) m
            #     Horizontal visibility. Dense fog: <50 m. Typical clear-sky air:
            #     10–20 km. Upper bound reflects ideal high-altitude or polar
            #     clear-air conditions.
            "visibility": Signal(attr="visibility_mean", raw=s["visibility_mean"][i], min=0.0, max=100000.0),
        }

        wmo_code = WeatherCode(s["weather_code"][i])
        rankings = self.determine_element_scores(signals=signals, weather_code=wmo_code)
        elements = filter_element_types(rankings)
        bonus_fx = ft.partial(lambda m: 2 if m.type in (*elements, types.VibemonTypeT.NORMAL) else 0.5)
        starters = {m: rankings[m.type] * bonus_fx(m) for m in moves.MOVES if m.level_requirement == 1}

        affinity = schema.Affinity(
            identity=schema.Identity(
                name="__",
                elements=elements,
                base_hp=base_stat_asymmetric_scaling(signals["spread"].normal, stat="hp"),
                base_attack=base_stat_asymmetric_scaling(signals["wind_gusts"].normal, stat="attack"),
                base_defense=base_stat_asymmetric_scaling(signals["elevation"].normal, stat="defense"),
                base_sp_attack=base_stat_asymmetric_scaling(signals["radiation"].normal, stat="sp_attack"),
                base_sp_defense=base_stat_asymmetric_scaling(signals["humidity"].normal, stat="sp_defense"),
                base_speed=base_stat_asymmetric_scaling(signals["wind_speed"].normal, stat="speed"),
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
