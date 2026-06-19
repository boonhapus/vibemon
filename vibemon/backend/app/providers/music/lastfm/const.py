"""Last.fm Web API constants."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "lastfm.web_api"

QUOTA_KEY: Final[str] = "lastfm"
RATE_LIMITS: Final[tuple[tuple[int, dt.timedelta], ...]] = ((300, dt.timedelta(minutes=1)),)
CONCURRENCY: Final[int] = 5
