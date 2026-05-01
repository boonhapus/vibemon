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
    def description(self) -> str:
        """Returns the descriptive mapping for the current weather code."""
        return _DESCRIPTIONS.get(self, "Unknown weather condition.")


# ── Metadata mapping ──────────────────────────────────────────────────────────────

_DESCRIPTIONS = {
    WeatherCode.CLEAR_SKY: "Open blue dome, sun-washed and still.",
    WeatherCode.MAINLY_CLEAR: "Mostly azure with thin, high wisps.",
    WeatherCode.PARTLY_CLOUDY: "Puffy white islands drifting across bright patches.",
    WeatherCode.OVERCAST: "Flat grey lid; soft, shadowless light everywhere.",
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP: "Dark towers and distant flicker, air charged but dry.",
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY: "Brooding mass, staccato lightning, thunder you feel in your chest.",
    WeatherCode.FOG: "Soft grey cocoon; edges dissolve a few steps ahead.",
    WeatherCode.DEPOSITING_RIME_FOG: "Icy breath on twigs and wires, fog that paints frost.",
    WeatherCode.DRIZZLE_LIGHT: "Fine mist veils surfaces without real sound.",
    WeatherCode.DRIZZLE_MODERATE: "Steady silver threads, everything lightly beaded.",
    WeatherCode.DRIZZLE_DENSE: "Heavy wet haze; drips run in constant ribbons.",
    WeatherCode.FREEZING_DRIZZLE_LIGHT: "Glassy needles that cling and glaze.",
    WeatherCode.FREEZING_DRIZZLE_DENSE: "Sheets of freezing mist building slick armour.",
    WeatherCode.RAIN_SLIGHT: "Sparse streaks; pavement goes speckled dark.",
    WeatherCode.RAIN_MODERATE: "Even curtains drumming roofs and gutters.",
    WeatherCode.RAIN_HEAVY: "Dense grey sheets; runoff races in sheets.",
    WeatherCode.FREEZING_RAIN_LIGHT: "Thin ice glaze forming as drops land.",
    WeatherCode.FREEZING_RAIN_HEAVY: "Encasing glaze, branches bow under crystal shells.",
    WeatherCode.SNOW_FALL_SLIGHT: "Sparse flakes spiralling in quiet hush.",
    WeatherCode.SNOW_FALL_MODERATE: "Steady white curtain muting distance.",
    WeatherCode.SNOW_FALL_HEAVY: "Thick blast, near-whiteout swirl and sting.",
    WeatherCode.SNOW_GRAINS: "Tiny icy grains ticking like dry sugar.",
    WeatherCode.RAIN_SHOWERS_SLIGHT: "Broken sun, sudden light spatters then calm.",
    WeatherCode.RAIN_SHOWERS_MODERATE: "On-off bursts drumming hard between gaps.",
    WeatherCode.RAIN_SHOWERS_VIOLENT: "Sideways slashes, wind-driven walls of water.",
    WeatherCode.SNOW_SHOWERS_SLIGHT: "Flurries under patchy sky, quick dustings.",
    WeatherCode.SNOW_SHOWERS_HEAVY: "Dense white bursts, visibility snaps shut.",
    WeatherCode.THUNDERSTORM: "Strobe sky, rolling thunder, rain in heavy rods.",
    WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL: "Electric chaos with ticking ice pellets on glass.",
    WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL: "Violent white flashes and hammering hail that dents rhythm.",
}