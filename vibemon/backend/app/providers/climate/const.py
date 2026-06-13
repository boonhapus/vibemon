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
    def visual_note_variants(self) -> tuple[str, ...]:
        """Creature-facing visual cue variants for the hatch-day weather code.

        Phrases must stay anatomy-neutral (palette, texture, markings, sheen) so the
        element body archetype keeps sole control of silhouette and body plan.
        """
        return _VISUAL_NOTES.get(self, _FALLBACK_VISUAL_NOTES)


# ── Creature visual notes per WMO code (rng-picked at birth for per-mon variety) ──

_FALLBACK_VISUAL_NOTES: tuple[str, ...] = ("changeable-sky mottling in mixed muted tones",)

_VISUAL_NOTES: dict[WeatherCode, tuple[str, ...]] = {
    WeatherCode.CLEAR_SKY: (
        "sun-bleached tones with harsh warm highlights",
        "white-gold glare sheen and sharp-edged warm shadows",
        "heat-faded palette with bright bleached patches",
    ),
    WeatherCode.MAINLY_CLEAR: (
        "warm bright base tones with pale sky-blue tip markings",
        "sunlit golden wash with thin cloud-wisp streaks",
        "clear-day brightness with powder-blue edging",
    ),
    WeatherCode.PARTLY_CLOUDY: (
        "soft white cloud-patch markings over sunlit tones",
        "drifting cloud-shadow dapples on a warm base",
        "broken-light mottling of bright and shaded patches",
    ),
    WeatherCode.OVERCAST: (
        "flat grey tones in shadowless muted light",
        "even pewter wash with no hard highlights",
        "dull silver-grey palette, soft and diffuse",
    ),
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP: (
        "dark storm-cloud mottling with crackling static shimmer",
        "bruised purple-grey tones with a static-charged sheen",
        "anvil-cloud gradient, slate above and charged pale below",
    ),
    WeatherCode.THUNDERSTORM_WITHOUT_PRECIP_HEAVY: (
        "charcoal tones with lightning-fork markings",
        "storm-black base split by jagged white vein markings",
        "deep thundercloud grey with electric-bright branching streaks",
    ),
    WeatherCode.FOG: (
        "soft grey tones fading at the edges like mist",
        "milk-white haze wash with blurred soft markings",
        "mist-muted palette with outlines gentled to grey",
    ),
    WeatherCode.DEPOSITING_RIME_FOG: (
        "frost-rimmed grey tones with ice-needle edging",
        "rime-crusted texture, every edge whitened with frost",
        "freezing-fog glaze, grey beneath crystalline white tips",
    ),
    WeatherCode.DRIZZLE_LIGHT: (
        "fine dew-beaded texture with a silvery mist sheen",
        "drizzle-speckled surface catching faint silver light",
        "thin damp gloss with scattered droplet flecks",
    ),
    WeatherCode.DRIZZLE_MODERATE: (
        "damp texture threaded with silver droplet lines",
        "steady drizzle sheen with colors darkened a half-step",
        "wet-silk gloss with beaded silver speckling",
    ),
    WeatherCode.DRIZZLE_DENSE: (
        "heavy wet sheen with colors dripping a tone darker",
        "soaked-through gloss, saturated and streaming",
        "dense drizzle glaze, every surface slick and dark",
    ),
    WeatherCode.FREEZING_DRIZZLE_LIGHT: (
        "needle-fine ice glaze on edges and tips",
        "thin frost-lacquer sheen over chilled tones",
        "delicate freezing-mist crystals dusting the surface",
    ),
    WeatherCode.FREEZING_DRIZZLE_DENSE: (
        "slick freezing glaze over a damp dark base",
        "thick ice-lacquer sheen, glassy and cold-toned",
        "hard frozen-drizzle crust with a wet shine beneath",
    ),
    WeatherCode.RAIN_SLIGHT: (
        "speckled rain-dark patches on dry-leaning tones",
        "first-rain stippling of scattered dark droplet marks",
        "light shower mottling, half wet and half dry",
    ),
    WeatherCode.RAIN_MODERATE: (
        "evenly rain-slicked texture, darkened and sleek",
        "steady-rain gloss deepening every color",
        "uniform wet sheen with clean rain-washed tones",
    ),
    WeatherCode.RAIN_HEAVY: (
        "dense rain-slick sheen, dripping and deep-toned",
        "downpour-darkened palette with streaming wet gloss",
        "saturated storm-wash with colors at their deepest",
    ),
    WeatherCode.FREEZING_RAIN_LIGHT: (
        "thin ice glaze over wet dark tones",
        "clear frozen lacquer over rain-darkened color",
        "glassy drip-ice sheen with cold pale highlights",
    ),
    WeatherCode.FREEZING_RAIN_HEAVY: (
        "thick crystal-ice glaze, glassy and heavy",
        "armoring clear-ice sheen over deep wet tones",
        "frozen-rain lacquer with trapped droplet flecks",
    ),
    WeatherCode.SNOW_FALL_SLIGHT: (
        "sparse snowflake flecks caught on quiet pale tones",
        "light snow-dusting over a hushed winter palette",
        "scattered white flecks on softly cooled colors",
    ),
    WeatherCode.SNOW_FALL_MODERATE: (
        "snow-dusted texture muting every color",
        "steady white powdering that softens all tones",
        "even snowfall veil, palette chilled and pale",
    ),
    WeatherCode.SNOW_FALL_HEAVY: (
        "packed snow crusting every surface white",
        "deep snow-caked texture, nearly whited out",
        "heavy snow-blanket tones, white over white",
    ),
    WeatherCode.SNOW_GRAINS: (
        "dry icy grain texture on sugar-pale tones",
        "coarse snow-grain stippling, frosted and matte",
        "granular ice-sugar dusting over winter pallor",
    ),
    WeatherCode.RAIN_SHOWERS_SLIGHT: (
        "patchy wet streaks flashing bright on sun-warmed tones",
        "sunshower speckling with glints of light in scattered rain marks",
        "quick shower stippling over warm bright patches",
    ),
    WeatherCode.RAIN_SHOWERS_MODERATE: (
        "restless on-off rain-darkened streaking",
        "shifting shower bands of wet-dark and drying-light stripes",
        "changeable rain mottling with half-soaked patches",
    ),
    WeatherCode.RAIN_SHOWERS_VIOLENT: (
        "wind-lashed sideways-soaked streaking",
        "driven-rain diagonal streaks, slicked flat and dark",
        "squall-battered wet sheen raked in one direction",
    ),
    WeatherCode.SNOW_SHOWERS_SLIGHT: (
        "quick flurry dustings over patchy pale markings",
        "passing snow-squall flecks on cool mottled tones",
        "light flurry speckling with white catching in patches",
    ),
    WeatherCode.SNOW_SHOWERS_HEAVY: (
        "dense snow crust blurring markings behind white",
        "whiteout squall caking with details muffled in snow",
        "heavy flurry layering, white drifted over every surface",
    ),
    WeatherCode.THUNDERSTORM: (
        "rain-dark tones with strobe-bright static shimmer",
        "storm-soaked palette lit by electric flicker highlights",
        "thunderhead grey-blue wash with charged white glints",
    ),
    WeatherCode.THUNDERSTORM_WITH_SLIGHT_HAIL: (
        "electric storm sheen with ice-pellet pockmarks",
        "static-charged tones dented by small hail stippling",
        "crackling storm wash with scattered hail-strike flecks",
    ),
    WeatherCode.THUNDERSTORM_WITH_HEAVY_HAIL: (
        "pitted storm-scarred texture with white flash markings",
        "hail-hammered dimpling under charcoal storm tones",
        "battle-worn storm patina, pale impact pocks on dark ground color",
    ),
}
