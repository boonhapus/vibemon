# P1-T3 — Weather Provider (Open-Meteo)

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T2
**Depends on this:** P1-T6

---

## Objective

Implement the first (and always-active) data source provider using the free Open-Meteo API. This provider maps temperature, wind, precipitation, humidity, and UV data to stat factors and element votes.

## Tasks

1. **Create `backend/app/providers/weather.py`**
   - Subclass `VibemonProvider`; `source_id = "weather"`
   - `fetch()` calls Open-Meteo's current weather endpoint:
     ```
     GET https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m,precipitation,relative_humidity_2m,uv_index,weather_code
     ```
   - Use `niquests` for the HTTP call (async)

2. **Map weather data to `SourceData` fields**
   Follow the provider mapping table from the design doc:
   - Temperature → element votes (Ice/Water/Grass/Fire/Ground based on thresholds)
   - Wind speed → `speed_factor` (normalised 0–80 km/h)
   - Precipitation > 5mm → `defense_factor` boost
   - Clear sky + high UV → `attack_factor` boost
   - Humidity → `hp_factor` (normalised 0–100%)
   - Hour 0–5 → Dark element vote (0.6)
   - Temperature cold→hot → `hue_primary` (190°→10° linear interpolation)

3. **Implement datetime-only fallback**
   - Create `backend/app/engine/fallback.py` with `datetime_only_source(timestamp, latitude)` function
   - Seasonal element assignment with Southern Hemisphere inversion
   - Speed from hour, attack from day of week
   - If Open-Meteo call fails, catch the exception and return `datetime_only_source()` result instead

4. **Set flavour text**
   - Include temperature, weather description, and city hint in `flavour_text`

5. **Register in `PROVIDER_REGISTRY`**

6. **Write tests**
   - Mock Open-Meteo response → verify correct stat factors and element votes
   - Test datetime-only fallback for both hemispheres
   - Test API failure → fallback path

## Acceptance Criteria

- Given lat/lon, returns a fully-populated `SourceData` with element votes and at least 3 stat factors set
- On API failure, gracefully returns datetime-only `SourceData`
- Element vote thresholds match the design doc table exactly

## Files Created

```
backend/app/
  providers/weather.py
  engine/fallback.py
tests/
  test_weather_provider.py
```
