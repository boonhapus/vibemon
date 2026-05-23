"""Shared primitive constrained types."""

from typing import Annotated

type UnitIntervalT = Annotated[float, "a clamped value between [0, 1]"]
