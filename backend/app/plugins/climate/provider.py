from typing import Final
import enum
import math
import statistics

from app.plugins.engine import Event, Vocabulary
from app.plugins.provider import VibeProvider
from app import schema, utils

from . import _const, _weather
from . import rules


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


class ClimateProvider(VibeProvider):
    """
    A data source which fetches the current weather.
    """

    name = "climate"
    ruleset = rules.WEATHER_RULESET

    def __init__(self) -> None:
        self.client = _weather.OpenMeteoAPIClient()

    @staticmethod
    def _norm(value: float, key: str) -> float:
        low, high = _BOUNDS[key]
        return utils.normalize(value, low=low, high=high)

    def _build_event(self, code: int) -> Event | None:
        for key, category, severity in _CODE_TABLE:
            if (code == key) if isinstance(key, int) else (code in key):
                return Event(category=category, severity=int(severity))
        return None

    @staticmethod
    def _calc_intensity(daily: dict, *, index: int) -> float:
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

    async def make_vocabulary(self, ctx: schema.BirthContext) -> Vocabulary:
        """Fetch and normalize weather data into identity vocabulary."""
        r = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        data = r.json()
        daily = data["daily"]
        index = -1

        apparent = daily["apparent_temperature_mean"]
        spread = max(apparent) - min(apparent)

        signals = {
            "temperature": self._norm(daily["temperature_2m_mean"][index], "temperature"),
            "temp_spread": self._norm(spread, "temp_spread"),
            "rain": self._norm(daily["rain_sum"][index], "rain"),
            "snow": self._norm(daily["snowfall_sum"][index], "snow"),
            "humidity": self._norm(daily["relative_humidity_2m_mean"][index], "humidity"),
            "dew_point": self._norm(daily["dew_point_2m_mean"][index], "dew_point"),
            "wind_speed": self._norm(daily["wind_speed_10m_max"][index], "wind_speed"),
            "wind_gusts": self._norm(daily["wind_gusts_10m_max"][index], "wind_gusts"),
            "uv_index": self._norm(daily["uv_index_max"][index], "uv_index"),
            "radiation": self._norm(daily["shortwave_radiation_sum"][index], "radiation"),
            "elevation": self._norm(data["elevation"], "elevation"),
            "visibility": self._norm(daily["visibility_mean"][index], "visibility"),
        }

        event = self._build_event(daily["weather_code"][index])
        intensity = self._calc_intensity(daily, index=index)

        return Vocabulary(signals=signals, event=event, intensity=intensity)

    async def teardown(self) -> None:
        """Clean up provider-owned resources."""
        await self.client.close()
