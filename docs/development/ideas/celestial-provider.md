# Celestial Provider

A Vibemon is born from the sky above its birthplace. The trainer's birth moment
— timestamp and coordinates already in BirthSeed — drives ephemeris calculation
for planetary positions, then folds into an `Affinity` through two lenses:
astronomical (observable sky facts) and astrological (symbolic chart).

Earth's place in the solar system is a **single computation**: planetary
positions, Sun-Moon-Earth angles, ecliptic coordinates. From that shared data
both layers derive their signals.

---

## Data Sources

None. Pure computation from existing BirthSeed fields (`timestamp`,
`geo_coords`, `local_timezone`). Uses ephemeris routines (e.g. Swiss Ephemeris
or `skyfield`) — zero external API calls, zero secrets, works offline.

---

## Signals Derived from Same Planetary Data

| Fact | Astronomy Reads | Astrology Reads |
|------|----------------|-----------------|
| Sun position | Day/night, season, solar altitude, dawn/dusk | Sun sign, house, dignity |
| Moon position | Moon phase (new → full), moonrise/set, distance | Moon sign, house, aspects |
| Planet positions | Which planets are above the horizon, magnitude, elongation | Sign + house for all 7 traditional planets |
| Sun-Moon angle | Phase illumination % | Lunation type, aspect orbs |
| Planet pairs | Conjunctions visible in sky | Aspect network (trines, squares, oppositions) |
| Horizon relation | Dusk/dawn/twilight phase | Angular house boundaries |

---

## Type Mapping

### From Astronomy (observable)

| Condition | Elements |
|-----------|----------|
| Daytime (sun above horizon) | ELECTRIC, FLYING |
| Nighttime (sun < −12°) | GHOST, DARK, PSYCHIC |
| Twilight (civil/naval/astro) | GHOST, FAIRY |
| Full moon (phase >0.85) | DARK, PSYCHIC (amplified) |
| New moon (phase <0.15) | GHOST, DARK |
| Waxing moon | FIRE, GRASS (growth) |
| Waning moon | WATER, ICE (recession) |
| Midwinter (solar solstice) | ICE, ROCK |
| Midsummer | FIRE, GRASS |
| Mercury visible | ELECTRIC, FLYING |
| Venus visible | FAIRY, WATER |
| Mars visible | FIRE, FIGHTING |
| Jupiter visible | DRAGON, PSYCHIC |
| Saturn visible | ROCK, DARK |
| Multiple planets visible simultaneously | PSYCHIC (stacked) |
| No planets visible (deep night, overcast analog) | GHOST |

### From Astrology (symbolic)

| Zodiac Triplicity | Elements |
|-------------------|----------|
| Fire signs (Aries, Leo, Sagittarius) | FIRE |
| Earth signs (Taurus, Virgo, Capricorn) | GROUND, ROCK |
| Air signs (Gemini, Libra, Aquarius) | FLYING, ELECTRIC |
| Water signs (Cancer, Scorpio, Pisces) | WATER, ICE |

| Planet | House / Angularity | Element Nudge |
|--------|--------------------|---------------|
| Sun in angular house (1/4/7/10) | FIRE, ELECTRIC boost |
| Moon in angular house | WATER, PSYCHIC boost |
| Saturn in cadent house | DARK, ROCK |
| Jupiter in succedent house | DRAGON, FAIRY |
| Many planets below horizon | GHOST, DARK, PSYCHIC |
| Many planets above horizon | FLYING, FIRE, ELECTRIC |

---

## Signal Design (6 stat axes)

| Stat | Signal | Computation |
|------|--------|-------------|
| HP | Celestial depth | How many planets are below horizon (hidden/enduring — unseen strength) |
| Attack | Mars prominence | Mars angularity × sign dignity (assertive energy) |
| Defense | Saturn prominence | Saturn angularity × sign dignity (discipline, structure) |
| Sp. Attack | Solar angularity | Sun house angularity × sign (will, identity projection) |
| Sp. Defense | Lunar angularity | Moon house angularity × sign (emotional resilience) |
| Speed | Mercury prominence | Mercury angularity × sign dignity (communication pace) |

All signals use a two-layer calculation: astronomical weight (is the body
visible? how high?) combined with astrological weight (house, sign, aspects).

---

## Intensity

Ratio of angular planets (bodies near ASC/MC/DC/IC) to total planets. A
chart with heavy angular concentration (all planets clustered near horizon or
zenith) yields high intensity. A scattered chart (planets evenly distributed)
yields low intensity.

Also nudged by lunation: new moon + eclipse season amplifies.

---

## Provider Notes

| Condition | Note |
| --------- | ---- |
| All planets clustered within 3 signs | `"Stellium concentration"` |
| Only Sun + Moon above horizon | `"Bare sky — most planets in daytime invisibility"` |
| Eclipse season (±15d of node) | `"Eclipse window — amplified intensity"` |
| Retrograde planets present | `"Retrograde influence"` |

---

## Moves

Celestial-themed move names in `data/moves.json` (e.g. Zenith, Nadir,
Retrograde, Eclipse, Trine, Lunar Standstill, Rising Sign, Opposition).

---

## Proposed Structure

```
providers/celestial/
  __init__.py              # re-export CelestialProvider
  provider.py              # CelestialProvider(VibeProvider)
  schema.py                # CelestialObservation, chart models
  const.py                 # Signs → VibemonTypeT, angularity tables
  data/
    moves.json
  ephemeris/
    __init__.py
    engine.py              # Ephemeris calculation (Skyfield / swisseph wrapper)
    models.py              # PlanetaryPosition, Chart, Aspect data types
  aspects.py               # Aspect detection, orbs, weighting
  houses.py                # House cusp calculation (Placidus / equal / whole)
```

---

## Wiring

Always available (no secrets needed). Added to the default provider list in
`scripts/_common.py` and `provider-options.ts` like climate and biome.
