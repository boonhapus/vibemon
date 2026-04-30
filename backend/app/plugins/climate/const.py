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
        return self._DESCRIPTIONS.get(self.value, "Unknown weather condition.")

    # ── Metadata mapping ──────────────────────────────────────────────────────────────

    _DESCRIPTIONS = {
         0: "Open blue dome, sun-washed and still.",
         1: "Mostly azure with thin, high wisps.",
         2: "Puffy white islands drifting across bright patches.",
         3: "Flat grey lid; soft, shadowless light everywhere.",
        13: "Dark towers and distant flicker, air charged but dry.",
        17: "Brooding mass, staccato lightning, thunder you feel in your chest.",
        45: "Soft grey cocoon; edges dissolve a few steps ahead.",
        48: "Icy breath on twigs and wires, fog that paints frost.",
        51: "Fine mist veils surfaces without real sound.",
        53: "Steady silver threads, everything lightly beaded.",
        55: "Heavy wet haze; drips run in constant ribbons.",
        56: "Glassy needles that cling and glaze.",
        57: "Sheets of freezing mist building slick armour.",
        61: "Sparse streaks; pavement goes speckled dark.",
        63: "Even curtains drumming roofs and gutters.",
        65: "Dense grey sheets; runoff races in sheets.",
        66: "Thin ice glaze forming as drops land.",
        67: "Encasing glaze, branches bow under crystal shells.",
        71: "Sparse flakes spiralling in quiet hush.",
        73: "Steady white curtain muting distance.",
        75: "Thick blast, near-whiteout swirl and sting.",
        77: "Tiny icy grains ticking like dry sugar.",
        80: "Broken sun, sudden light spatters then calm.",
        81: "On-off bursts drumming hard between gaps.",
        82: "Sideways slashes, wind-driven walls of water.",
        85: "Flurries under patchy sky, quick dustings.",
        86: "Dense white bursts, visibility snaps shut.",
        95: "Strobe sky, rolling thunder, rain in heavy rods.",
        96: "Electric chaos with ticking ice pellets on glass.",
        99: "Violent white flashes and hammering hail that dents rhythm.",
    }