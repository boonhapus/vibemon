from typing import Final
import enum
import math
import statistics

from app.plugins.provider import VibeProvider
from app.plugins import helpers
from app import schema, types

from . import _const, _weather
from . import moves


class _Severity(enum.IntEnum):
    NONE = 0
    LIGHT = 1
    MODERATE = 2
    HEAVY = 3


_BOUNDS: Final[dict[str, tuple[float, float]]] = {
    "temperature": (-30.0, 50.0),
    "temp_spread": (1.0, 20.0),
    "rain": (0.0, 50.0),
    "snow": (0.0, 20.0),
    "humidity": (5.0, 95.0),
    "dew_point": (-40.0, 35.0),
    "wind_speed": (3.0, 55.0),
    "wind_gusts": (5.0, 90.0),
    "uv_index": (0.0, 14.0),
    "radiation": (1.0, 32.0),
    "elevation": (0.0, 3500.0),
    "visibility": (0.0, 100000.0),
}

_CODE_TABLE: Final[list[tuple[range | int, str, _Severity]]] = [
    (_const.WeatherCode.CLEAR_SKY, "clear", _Severity.LIGHT),
    (range(1, 4), "cloudy", _Severity.LIGHT),
    (_const.WeatherCode.THUNDERSTORM_WITHOUT_PRECIP, "thunderstorm", _Severity.MODERATE),
    (_const.WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY, "thunderstorm", _Severity.HEAVY),
    (range(30, 36), "dust_storm", _Severity.MODERATE),
    (range(40, 50), "fog", _Severity.MODERATE),
    (range(50, 56), "drizzle", _Severity.MODERATE),
    (range(56, 58), "freezing_drizzle", _Severity.MODERATE),
    (range(58, 60), "drizzle", _Severity.MODERATE),
    (range(60, 66), "rain", _Severity.HEAVY),
    (range(66, 68), "freezing_rain", _Severity.HEAVY),
    (range(68, 70), "rain", _Severity.HEAVY),
    (_const.WeatherCode.SNOW_GRAINS, "snow_grains", _Severity.MODERATE),
    (range(70, 80), "snow", _Severity.HEAVY),
    (range(80, 83), "rain_showers", _Severity.MODERATE),
    (range(83, 87), "rain_with_snow", _Severity.MODERATE),
    (range(87, 91), "hail", _Severity.MODERATE),
    (range(91, 100), "thunderstorm", _Severity.HEAVY),
]

_MOVE_BY_NAME = {m.name: m for m in moves.MOVES}

_VISUAL_NOTES: Final[dict[str, str]] = {
    "clear": "Clear, high-contrast form with sharp edge-geometry.",
    "cloudy": "Semi-translucent with soft internal refraction.",
    "fog": "Diffuse, low-opacity silhouette shrouded in mist.",
    "drizzle": "Glistening exterior with constant particle-drip effects.",
    "freezing_drizzle": "Glassy ice veneer forming over a drip-textured surface.",
    "rain": "Streaming liquid channels carved across the form.",
    "freezing_rain": "Smooth ice casing with trapped liquid veins beneath.",
    "rain_showers": "Burst-pattern splash rings radiating outward on impact.",
    "snow": "Frosted crystalline armor with soft powder layering.",
    "snow_grains": "Micro-crystal shimmer suspended around the silhouette.",
    "rain_with_snow": "Slushy cascade mixing rain streaks with snow clumps.",
    "hail": "Pitted ice-stone exterior, jagged where impacts have landed.",
    "thunderstorm": "Volatile storm-wracked form with lightning-threaded contours.",
    "dust_storm": "Granular, wind-scoured silhouette wreathed in airborne grit.",
}
_DEFAULT_NOTE = "Neutral, undefined form."


class ClimateProvider(VibeProvider):
    name = "climate"

    def __init__(self) -> None:
        self.client = _weather.OpenMeteoAPIClient()

    def _normalize(self, value: float, key: str) -> float:
        low, high = _BOUNDS[key]
        return helpers.normalize(value, low=low, high=high)

    def _get_event_category_and_severity(self, code: int) -> tuple[str | None, _Severity]:
        for key, category, severity in _CODE_TABLE:
            if (code == key) if isinstance(key, int) else (code in key):
                return category, severity
        return None, _Severity.NONE

    def _severity_multiplier(self, severity: _Severity) -> float:
        severity_scale = (0.0, 0.15, 0.30, 0.45)
        return severity_scale[int(severity)]

    def _calc_intensity(self, daily: dict, *, index: int) -> float:
        z_keys: Final[tuple[str, ...]] = (
            "apparent_temperature_mean",
            "wind_gusts_10m_max",
            "relative_humidity_2m_mean",
            "shortwave_radiation_sum",
        )
        z_scores: list[float] = []
        for key in z_keys:
            history = daily[key]
            if len(history) < 2:
                continue
            mean = statistics.mean(history)
            stdev = statistics.stdev(history)
            if stdev > 0:
                z_scores.append((history[index] - mean) / stdev)

        if not z_scores:
            return 0.5

        most_deviant = max(z_scores, key=abs)
        return round(1.0 / (1.0 + math.exp(-most_deviant)), 4)

    def _build_element_scores(
        self, signals: dict[str, float], event_category: str | None, severity: _Severity
    ) -> dict[types.VibemonTypeT, float]:
        scores: dict[types.VibemonTypeT, float] = {}

        # Thermal
        temp = signals["temperature"]
        if temp > 0.40:
            scores[types.VibemonTypeT.FIRE] = (temp - 0.40) / 0.60
        if temp <= 0.70:
            scores[types.VibemonTypeT.ICE] = (1.0 - temp - 0.30) / 0.70

        # Moisture
        scores[types.VibemonTypeT.WATER] = signals["rain"]
        scores[types.VibemonTypeT.ICE] = scores.get(types.VibemonTypeT.ICE, 0) + signals["snow"]

        dew = signals["dew_point"]
        if dew > 0.30:
            scores[types.VibemonTypeT.GRASS] = (dew - 0.30) / 0.70
            scores[types.VibemonTypeT.GROUND] = scores.get(types.VibemonTypeT.GROUND, 0)
        else:
            scores[types.VibemonTypeT.GROUND] = scores.get(types.VibemonTypeT.GROUND, 0) + 1.0

        if signals["humidity"] > 0.60:
            scores[types.VibemonTypeT.POISON] = (signals["humidity"] - 0.60) / 0.40

        # Kinetic
        if signals["wind_speed"] > 0.20:
            scores[types.VibemonTypeT.FLYING] = (signals["wind_speed"] - 0.20) / 0.80

        # Solar
        if signals["uv_index"] > 0.30:
            scores[types.VibemonTypeT.ELECTRIC] = (signals["uv_index"] - 0.30) / 0.70

        # Terrain - elevation contributes to BOTH rock and ground
        if signals["elevation"] > 0.25:
            scores[types.VibemonTypeT.ROCK] = (signals["elevation"] - 0.25) / 0.75
        scores[types.VibemonTypeT.GROUND] = scores.get(types.VibemonTypeT.GROUND, 0) + signals["elevation"]

        # Atmospheric
        vis = signals["visibility"]
        if vis <= 0.60:
            scores[types.VibemonTypeT.GHOST] = (0.60 - vis) / 0.60
        if vis <= 0.25:
            scores[types.VibemonTypeT.DARK] = (0.25 - vis) / 0.25

        # Event contributions
        if event_category:
            event_affinities = {
                "clear": [(types.VibemonTypeT.FIRE, 1.0)],
                "cloudy": [(types.VibemonTypeT.NORMAL, 1.0)],
                "fog": [(types.VibemonTypeT.GHOST, 1.0)],
                "drizzle": [(types.VibemonTypeT.WATER, 1.0)],
                "freezing_drizzle": [(types.VibemonTypeT.ICE, 1.0), (types.VibemonTypeT.WATER, 0.5)],
                "rain": [(types.VibemonTypeT.WATER, 1.0)],
                "freezing_rain": [(types.VibemonTypeT.ICE, 1.0), (types.VibemonTypeT.WATER, 0.5)],
                "rain_showers": [(types.VibemonTypeT.WATER, 1.0)],
                "snow": [(types.VibemonTypeT.ICE, 1.0)],
                "snow_grains": [(types.VibemonTypeT.ICE, 0.5)],
                "rain_with_snow": [(types.VibemonTypeT.ICE, 1.0), (types.VibemonTypeT.WATER, 0.5)],
                "hail": [(types.VibemonTypeT.ICE, 1.0), (types.VibemonTypeT.ROCK, 0.5)],
                "thunderstorm": [(types.VibemonTypeT.ELECTRIC, 1.0)],
                "dust_storm": [(types.VibemonTypeT.GROUND, 1.0)],
            }
            severity_mult = self._severity_multiplier(severity)
            for element, weight in event_affinities.get(event_category, []):
                scores[element] = scores.get(element, 0) + weight * severity_mult

        return scores

    def _build_move_weights(
        self, signals: dict[str, float], event_category: str | None, severity: _Severity
    ) -> dict[schema.Move, float]:
        weighted: dict[schema.Move, float] = {}

        def add_moves(move_names: list[str], weight: float) -> None:
            for name in move_names:
                move = _MOVE_BY_NAME[name]
                weighted[move] = weighted.get(move, 0) + weight

        # Signal-based moves
        add_moves(["Heat Index Surge", "Scorching High", "Sunstroke Beam"], signals["temperature"] * 0.8)
        add_moves(["Black Ice Shard", "Rime Needle"], (1 - signals["temperature"]) * 0.9)
        add_moves(["Polar Vortex Clamp", "Heat Index Surge", "Monsoon Spiral"], signals["temp_spread"] * 0.6)
        add_moves(["Sheet Rain", "Downpour Driver", "Drizzle Needle", "Monsoon Spiral"], signals["rain"] * 0.9)
        add_moves(["Hail Core Pelting", "Flash Freeze", "Black Ice Shard"], signals["snow"] * 0.9)
        add_moves(["Dew Point Bloom", "Muggy Spore Drift", "Humid Root Grasp"], signals["humidity"] * 0.7)
        add_moves(["Dew Point Bloom", "Canopy Whip", "Saturated Soil Hook"], signals["dew_point"] * 0.8)
        add_moves(["Gust Front", "Crosswind Cut", "Anemometer Spin"], signals["wind_speed"] * 0.9)
        add_moves(["Downdraft Slam", "Jet Stream Shear", "Cloud-to-Ground Bolt"], signals["wind_gusts"] * 0.9)
        add_moves(["UV Microflare", "Sunstroke Beam", "Sheet Lightning Glow"], signals["uv_index"] * 0.8)
        add_moves(["Thermal Shimmer Lash", "UV Microflare", "Static Hair Snap"], signals["radiation"] * 0.8)
        add_moves(["Crag Silhouette", "Boulder Outcrop", "Contour Line Burrow"], signals["elevation"] * 0.9)
        add_moves(["Fog Echo", "Vapor Wisp", "Visibility Zero Trench", "Curfew Veil"], signals["visibility"] * 0.8)

        # Event-based moves
        if event_category:
            event_moves = {
                "clear": ["Fair Skies Nod", "Isobaric Calm", "Scorching High"],
                "cloudy": ["Partly Cloudy Glance", "Station Model Shrug"],
                "fog": ["Fog Echo", "Vapor Wisp", "Deck Fog Roll"],
                "drizzle": ["Drizzle Needle", "Sheet Rain"],
                "freezing_drizzle": ["Flash Freeze", "Black Ice Shard"],
                "rain": ["Downpour Driver", "Sheet Rain"],
                "freezing_rain": ["Hail Core Pelting", "Flash Freeze"],
                "rain_showers": ["Monsoon Spiral", "Sheet Rain"],
                "snow": ["Polar Vortex Clamp", "Rime Needle"],
                "snow_grains": ["Rime Needle", "Hail Core Pelting"],
                "rain_with_snow": ["Hail Core Pelting", "Downpour Driver"],
                "hail": ["Hail Core Pelting", "Landslip Hammer"],
                "thunderstorm": ["Thunderhead Core", "Cloud-to-Ground Bolt", "Ionized Gust"],
                "dust_storm": ["Isobar Stamp", "Saturated Soil Hook", "Landslip Hammer"],
            }
            severity_mult = self._severity_multiplier(severity)
            for move_name in event_moves.get(event_category, []):
                move = _MOVE_BY_NAME[move_name]
                weighted[move] = weighted.get(move, 0) + 0.8 * severity_mult

        return weighted

    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        r = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        data = r.json()
        daily = data["daily"]
        index = -1

        # Normalize signals
        apparent = daily["apparent_temperature_mean"]
        spread = max(apparent) - min(apparent)

        signals = {
            "temperature": self._normalize(daily["temperature_2m_mean"][index], "temperature"),
            "temp_spread": self._normalize(spread, "temp_spread"),
            "rain": self._normalize(daily["rain_sum"][index], "rain"),
            "snow": self._normalize(daily["snowfall_sum"][index], "snow"),
            "humidity": self._normalize(daily["relative_humidity_2m_mean"][index], "humidity"),
            "dew_point": self._normalize(daily["dew_point_2m_mean"][index], "dew_point"),
            "wind_speed": self._normalize(daily["wind_speed_10m_max"][index], "wind_speed"),
            "wind_gusts": self._normalize(daily["wind_gusts_10m_max"][index], "wind_gusts"),
            "uv_index": self._normalize(daily["uv_index_max"][index], "uv_index"),
            "radiation": self._normalize(daily["shortwave_radiation_sum"][index], "radiation"),
            "elevation": self._normalize(data["elevation"], "elevation"),
            "visibility": self._normalize(daily["visibility_mean"][index], "visibility"),
        }

        # Get event category and severity
        event_category, severity = self._get_event_category_and_severity(daily["weather_code"][index])

        # Build elements
        element_scores = self._build_element_scores(signals, event_category, severity)
        elements = helpers.select_elements(element_scores)

        # Build stats using asymmetric scaling
        stats = {
            "base_hp": helpers.base_stat_asymmetric_scaling(signals["temp_spread"], "base_hp"),
            "base_attack": helpers.base_stat_asymmetric_scaling(signals["wind_gusts"], "base_attack"),
            "base_defense": helpers.base_stat_asymmetric_scaling(signals["elevation"], "base_defense"),
            "base_sp_attack": helpers.base_stat_asymmetric_scaling(signals["radiation"], "base_sp_attack"),
            "base_sp_defense": helpers.base_stat_asymmetric_scaling(signals["humidity"], "base_sp_defense"),
            "base_speed": helpers.base_stat_asymmetric_scaling(signals["wind_speed"], "base_speed"),
        }

        # Build and sample moves
        move_weights = self._build_move_weights(signals, event_category, severity)
        moves = helpers.sample_move_pool(move_weights)

        # Calculate intensity
        intensity = self._calc_intensity(daily, index=index)

        # Generate visual note
        visual_notes = _VISUAL_NOTES.get(event_category, _DEFAULT_NOTE) if event_category else _DEFAULT_NOTE

        return schema.Affinity(
            identity=schema.Identity(name="__", elements=elements, **stats),
            visual_notes=visual_notes,
            intensity=intensity,
            provider_id=self.name,
            moves=moves,
        )

    async def teardown(self) -> None:
        await self.client.close()
