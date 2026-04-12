from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from app.domain.context import SourceData


def datetime_only_source(
    timestamp: datetime, latitude: Optional[float] = None
) -> SourceData:
    hour = timestamp.hour
    dow = timestamp.weekday()

    southern = (latitude is not None) and (latitude < 0)
    adjusted_month = ((timestamp.month - 1 + 6) % 12) + 1 if southern else timestamp.month

    speed_factor = float(math.sin(math.pi * hour / 23.0))
    attack_factor = 0.4 if dow >= 5 else 0.3 + (dow / 4.0) * 0.6

    season_elements: list[tuple[tuple[int, ...], str]] = [
        ((12, 1, 2), "Ice"),
        ((3, 4, 5), "Grass"),
        ((6, 7, 8), "Fire"),
        ((9, 10, 11), "Water"),
    ]
    element = next(e for months, e in season_elements if adjusted_month in months)

    return SourceData(
        speed_factor=speed_factor,
        attack_factor=attack_factor,
        element_votes=[(element, 1.0)],
        flavour_text=f"Born from the {timestamp.strftime('%A')} silence",
        raw={"weather_live": False},
    )
