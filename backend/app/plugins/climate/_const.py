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
