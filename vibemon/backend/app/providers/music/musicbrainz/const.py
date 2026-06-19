"""MusicBrainz Web API constants."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "musicbrainz.web_api"

QUOTA_KEY: Final[str] = "musicbrainz"
RATE_LIMITS: Final[tuple[tuple[int, dt.timedelta], ...]] = ((25, dt.timedelta(seconds=1)),)
