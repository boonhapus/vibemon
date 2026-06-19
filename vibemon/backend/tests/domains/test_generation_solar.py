import datetime as dt

from app.domains.generation.seed import BirthSeed
from tests.conftest import TEST_TRAINER_ID


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
