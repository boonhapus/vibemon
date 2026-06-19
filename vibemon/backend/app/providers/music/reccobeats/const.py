"""ReccoBeats API constants."""

from typing import Final
import datetime as dt

PROVIDER_NAME: Final[str] = "reccobeats.audio_analysis"

QUOTA_KEY: Final[str] = "reccobeats"
RATE_LIMITS: Final[tuple[tuple[int, dt.timedelta], ...]] = ((300, dt.timedelta(minutes=1)),)
