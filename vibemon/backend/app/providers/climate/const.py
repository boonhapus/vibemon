import enum


class WeatherCode(enum.IntEnum):
    """
    WMO Code 4677 weather code values used by climate provider mappings.

    Open-Meteo commonly returns a subset of these values, but this enum also
    includes two lower-range thunderstorm codes used by our canonical mapping.
    """

    CLEAR_SKY = 0
    MAINLY_CLEAR = 1
    PARTLY_CLOUDY = 2
    OVERCAST = 3

    THUNDERSTORM_WITHOUT_PRECIP = 13
    THUNDERSTORM_WITHOUT_PRECIP_HEAVY = 17

    FOG = 45
    DEPOSITING_RIME_FOG = 48

    DRIZZLE_LIGHT = 51
    DRIZZLE_MODERATE = 53
    DRIZZLE_DENSE = 55
    FREEZING_DRIZZLE_LIGHT = 56
    FREEZING_DRIZZLE_DENSE = 57

    RAIN_SLIGHT = 61
    RAIN_MODERATE = 63
    RAIN_HEAVY = 65
    FREEZING_RAIN_LIGHT = 66
    FREEZING_RAIN_HEAVY = 67

    SNOW_FALL_SLIGHT = 71
    SNOW_FALL_MODERATE = 73
    SNOW_FALL_HEAVY = 75
    SNOW_GRAINS = 77

    RAIN_SHOWERS_SLIGHT = 80
    RAIN_SHOWERS_MODERATE = 81
    RAIN_SHOWERS_VIOLENT = 82
    SNOW_SHOWERS_SLIGHT = 85
    SNOW_SHOWERS_HEAVY = 86

    THUNDERSTORM = 95
    THUNDERSTORM_WITH_SLIGHT_HAIL = 96
    THUNDERSTORM_WITH_HEAVY_HAIL = 99

    @property
    def visual_note(self) -> str:
        """Creature-facing visual cue for the hatch-day weather code."""
        return _VISUAL_NOTES.get(self, "weather-marked hide with unclear sky cues")


# ── Creature visual notes per WMO code ────────────────────────────────────────────

_VISUAL_NOTES = {
    WeatherCode.CLEAR_SKY: "sun-bleached hide with harsh warm highlights",
    WeatherCode.MAINLY_CLEAR: "warm bright coat with pale sky-blue tip markings",
    WeatherCode.PARTLY_CLOUDY: "soft white cloud patches on sunlit fur",
    WeatherCode.OVERCAST: "flat grey fur in shadowless muted tones",
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP: "dark storm-cloud mantle with crackling spine static",
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY: "charcoal hide with lightning-fork markings",
    WeatherCode.FOG: "soft grey fur fading at the edges like mist",
    WeatherCode.DEPOSITING_RIME_FOG: "frost-rimmed grey coat with ice needles on every edge",
    WeatherCode.DRIZZLE_LIGHT: "fine dew-beaded fur with a silvery mist sheen",
    WeatherCode.DRIZZLE_MODERATE: "damp coat threaded with silver droplets",
    WeatherCode.DRIZZLE_DENSE: "heavy wet sheen with fur dripping in ribbons",
    WeatherCode.FREEZING_DRIZZLE_LIGHT: "needle-fine ice glaze on fur tips",
    WeatherCode.FREEZING_DRIZZLE_DENSE: "slick freezing armour over damp undercoat",
    WeatherCode.RAIN_SLIGHT: "speckled rain-dark patches on dry-leaning fur",
    WeatherCode.RAIN_MODERATE: "evenly rain-slicked coat darkened and sleek",
    WeatherCode.RAIN_HEAVY: "dense rain-slick fur dripping and deep-toned",
    WeatherCode.FREEZING_RAIN_LIGHT: "thin ice shell glazing wet fur",
    WeatherCode.FREEZING_RAIN_HEAVY: "crystal ice encasement bowing limbs under weight",
    WeatherCode.SNOW_FALL_SLIGHT: "sparse snowflakes caught in quiet pale fur",
    WeatherCode.SNOW_FALL_MODERATE: "snow-dusted coat muting every color",
    WeatherCode.SNOW_FALL_HEAVY: "packed snow crusting the whole body white",
    WeatherCode.SNOW_GRAINS: "dry icy grain texture on sugar-pale hide",
    WeatherCode.RAIN_SHOWERS_SLIGHT: "patchy wet streaks flashing bright on sun-warmed fur",
    WeatherCode.RAIN_SHOWERS_MODERATE: "restless coat with on-off rain-darkened streaks",
    WeatherCode.RAIN_SHOWERS_VIOLENT: "wind-lashed fur clinging flat, sideways-soaked",
    WeatherCode.SNOW_SHOWERS_SLIGHT: "quick flurry dustings over patchy pale markings",
    WeatherCode.SNOW_SHOWERS_HEAVY: "dense snow crust blurring features behind white",
    WeatherCode.THUNDERSTORM: "rain-dark fur with strobe-bright static crest",
    WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL: "electric coat with ice-pellet pockmarks",
    WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL: "pitted storm-scarred hide with white flash marks",
}
