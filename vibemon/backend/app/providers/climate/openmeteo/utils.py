import datetime as dt

from . import const


def resolve_date_range(
    *,
    start_date: dt.date | None,
    end_date: dt.date | None,
) -> tuple[dt.date, dt.date]:
    if end_date is None:
        end_date = dt.datetime.now(tz=dt.UTC).date()

    assert isinstance(end_date, dt.date), "end_date must be provided."

    if start_date is None:
        start_date = end_date - const.DEFAULT_LOOKBACK

    assert isinstance(start_date, dt.date), "start_date must be provided."
    assert start_date < end_date, "Time range must be contiguous, start_date < end_date."

    return start_date, end_date
