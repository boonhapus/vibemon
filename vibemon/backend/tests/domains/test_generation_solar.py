import datetime as dt

from app.domains.generation import types as generation_types
from app.domains.generation.seed import BirthSeed
from tests.conftest import TEST_TRAINER_ID


def test_solar_phase_at_equatorial_noon() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 6, 21, 12, 0, tzinfo=dt.UTC),
        geo_coords=(0.0, 0.0),
        trainer_id=TEST_TRAINER_ID,
        providers=[],
    )
    assert seed.solar_phase is generation_types.SolarPhase.DAY


def test_solar_phase_at_high_latitude_winter_midnight() -> None:
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 12, 21, 0, 0, tzinfo=dt.UTC),
        geo_coords=(72.0, 0.0),
        trainer_id=TEST_TRAINER_ID,
        providers=[],
    )
    assert seed.solar_phase is generation_types.SolarPhase.NIGHT


def test_local_time_uses_local_timezone() -> None:
    local_tz = dt.timezone(dt.timedelta(hours=-6))
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 6, 21, 18, 0, tzinfo=dt.UTC),
        geo_coords=(41.8781, -87.6298),
        local_timezone=local_tz,
        trainer_id=TEST_TRAINER_ID,
        providers=[],
    )
    assert seed.local_time == dt.datetime(2026, 6, 21, 12, 0, tzinfo=local_tz)
