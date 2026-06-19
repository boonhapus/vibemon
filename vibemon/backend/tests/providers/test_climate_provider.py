from typing import Any, cast
import collections
import datetime as dt
import random

import pytest

from app.domains.generation.seed import BirthSeed
from app.domains.move import universal
from app.providers.climate.const import WeatherCode
from app.providers.climate.provider import ClimateProvider
from app.providers.climate.schema import ClimatePayload
from tests.conftest import TEST_TRAINER_ID


def _climate_payload(**overrides: Any) -> ClimatePayload:
    daily_defaults: dict[str, list[Any]] = {
        "time": ["2026-05-18", "2026-05-19"],
        "weather_code": [3, 0],
        "cape_mean": [100.0, 100.0],
        "cloud_cover_mean": [60.0, 60.0],
        "dew_point_2m_mean": [10.0, 10.0],
        "dust_mean": [15.0, 15.0],
        "et0_fao_evapotranspiration": [3.5, 3.5],
        "pm2_5_mean": [25.0, 25.0],
        "precipitation_sum": [1.5, 1.5],
        "relative_humidity_2m_mean": [65.0, 65.0],
        "shortwave_radiation_sum": [15.0, 15.0],
        "snowfall_sum": [0.1, 0.1],
        "temperature_2m_max": [20.0, 20.0],
        "temperature_2m_min": [8.0, 8.0],
        "uv_index_max": [6.0, 6.0],
        "visibility_mean": [15000.0, 15000.0],
        "wind_gusts_10m_max": [30.0, 30.0],
        "wind_speed_10m_max": [15.0, 15.0],
    }
    daily_defaults.update(overrides.get("daily", {}))
    weather_augmented = {"elevation": overrides.get("elevation", 350.0), "daily": daily_defaults}
    return ClimatePayload(
        start_date="2026-05-01",
        end_date="2026-05-19",
        weather_augmented=weather_augmented,
    )


def test_visual_notes_clear_sky_creature_cues() -> None:
    provider = ClimateProvider()
    payload = _climate_payload(daily={"weather_code": [3, WeatherCode.CLEAR_SKY]})
    signals = provider.derive_signals(payload)

    notes = provider.visual_notes(weather_code=WeatherCode.CLEAR_SKY, signals=signals, rng=random.Random(0))

    assert notes in WeatherCode.CLEAR_SKY.visual_note_variants
    assert "pavement" not in notes
    assert "dome" not in notes


def test_visual_notes_dust_accent_on_clear_day() -> None:
    provider = ClimateProvider()
    payload = _climate_payload(
        daily={
            "weather_code": [3, WeatherCode.CLEAR_SKY],
            "dust_mean": [15.0, 900.0],
        }
    )
    signals = provider.derive_signals(payload)

    notes = provider.visual_notes(weather_code=WeatherCode.CLEAR_SKY, signals=signals, rng=random.Random(0))

    base, accent = notes.split("; ")
    assert base in WeatherCode.CLEAR_SKY.visual_note_variants
    assert accent == "grit-streaked dust film"


def test_visual_notes_skips_redundant_wind_accent() -> None:
    provider = ClimateProvider()
    payload = _climate_payload(
        daily={
            "weather_code": [3, WeatherCode.RAIN_SHOWERS_VIOLENT],
            "wind_speed_10m_max": [15.0, 120.0],
        }
    )
    signals = provider.derive_signals(payload)

    notes = provider.visual_notes(weather_code=WeatherCode.RAIN_SHOWERS_VIOLENT, signals=signals, rng=random.Random(0))

    assert notes in WeatherCode.RAIN_SHOWERS_VIOLENT.visual_note_variants
    assert "wind-raked streaking" not in notes


def test_visual_notes_vary_across_rng_streams() -> None:
    provider = ClimateProvider()
    payload = _climate_payload(daily={"weather_code": [3, WeatherCode.FOG]})
    signals = provider.derive_signals(payload)

    picked = {
        provider.visual_notes(weather_code=WeatherCode.FOG, signals=signals, rng=random.Random(i)) for i in range(20)
    }

    assert len(picked) > 1
    assert picked <= set(WeatherCode.FOG.visual_note_variants)


@pytest.mark.asyncio
async def test_synthesize_visual_notes_are_replay_safe() -> None:
    provider = ClimateProvider()
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC),
        geo_coords=(40.7128, -74.0060),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = _climate_payload(daily={"weather_code": [3, WeatherCode.FOG]})

    first = await provider.synthesize(seed, payload)
    second = await provider.synthesize(seed, payload)

    assert first.visual_notes in WeatherCode.FOG.visual_note_variants
    assert first.visual_notes == second.visual_notes


def test_calculate_intensity_handles_missing_visibility() -> None:
    daily = cast(
        dict[str, list[float | None]],
        {
            "temperature_2m_max": [20.0, 22.0, 18.0],
            "temperature_2m_min": [8.0, 10.0, 6.0],
            "precipitation_sum": [1.5, 0.0, 2.0],
            "wind_gusts_10m_max": [30.0, 25.0, 35.0],
            "cape_mean": [100.0, 80.0, 120.0],
            "visibility_mean": [15000.0, None, 12000.0],
        },
    )

    intensity = ClimateProvider().calculate_intensity(daily, index=-1)

    assert 0.0 <= intensity <= 1.0


def _flat_window(hatch: dict[str, float]) -> dict[str, list[float | None]]:
    """Build a 6-day window of mundane baseline days, then append one hatch day."""
    baseline = {
        "temperature_2m_max": 20.0,
        "temperature_2m_min": 8.0,
        "precipitation_sum": 1.5,
        "wind_gusts_10m_max": 30.0,
        "cape_mean": 100.0,
        "visibility_mean": 15000.0,
    }
    return cast(
        dict[str, list[float | None]],
        {key: [baseline[key]] * 6 + [hatch.get(key, baseline[key])] for key in baseline},
    )


def test_intensity_typical_day_sits_on_soft_floor() -> None:
    # A hatch day matching its baseline is common — it should land near the ~0.30 floor.
    intensity = ClimateProvider().calculate_intensity(_flat_window({}), index=-1)

    assert 0.25 <= intensity <= 0.35


def test_intensity_is_symmetric_for_temperature_extremes() -> None:
    # A record-cold hatch day is as rare as a record-hot one, so both score high.
    provider = ClimateProvider()
    heat = provider.calculate_intensity(_flat_window({"temperature_2m_max": 45.0}), index=-1)
    cold = provider.calculate_intensity(_flat_window({"temperature_2m_min": -25.0}), index=-1)

    assert heat > 0.6
    assert cold > 0.6


def test_intensity_ignores_calm_dry_tail() -> None:
    # A drier/calmer-than-baseline day is common, not rare — stays on the floor.
    calm = ClimateProvider().calculate_intensity(
        _flat_window({"precipitation_sum": 0.0, "wind_gusts_10m_max": 5.0}), index=-1
    )

    assert calm <= 0.35


def test_climate_move_catalog_has_fifteen_moves_per_exposed_element() -> None:
    provider = ClimateProvider()
    exposed_types = set(provider.get_exposed_elements())

    catalog_types = {move.type for move in provider.moves()}
    move_counts = collections.Counter(move.type for move in provider.moves())

    assert catalog_types <= exposed_types
    assert move_counts == {element: 15 for element in exposed_types}


def test_climate_starter_moves_include_shared_universal_moves_once() -> None:
    provider = ClimateProvider()

    universal_ids = {move.id for move in universal.moves()}
    starter_ids = [move.id for move in provider.starter_moves(level=99)]

    assert universal_ids <= set(starter_ids)
    assert len(starter_ids) == len(set(starter_ids))
    assert len(starter_ids) == len(provider.moves()) + len(universal.moves())
