from __future__ import annotations

from datetime import datetime, timezone

from app.domain.fallback import datetime_only_source


def test_datetime_only_southern_inverts_season() -> None:
    ts = datetime(2024, 7, 15, 12, tzinfo=timezone.utc)
    north = datetime_only_source(ts, latitude=40.0)
    south = datetime_only_source(ts, latitude=-40.0)
    n_el = north.element_votes[0][0]
    s_el = south.element_votes[0][0]
    assert n_el != s_el
