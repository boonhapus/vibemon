import pydantic
import structlog

from app import types, utils

_LOGGER = structlog.get_logger(__name__)


class Signal(pydantic.BaseModel):
    """Apply binding to raw data."""
    attr: str
    raw: float
    min: float
    max: float

    @pydantic.computed_field
    @property
    def normal(self) -> types.UnitIntervalT:
        """Map raw value to 0-1 range, clamped to [0.0, 1.0]."""
        clamped = utils.clamp(self.raw, minimum=self.min, maximum=self.max)
        return (clamped - self.min) / (self.max - self.min)


def filter_element_types(
    scores: dict[types.VibemonTypeT, float],
    thresh_primary: float = 0.20,
    thresh_secondary: float = 0.75,
) -> tuple[types.VibemonTypeT, ...]:
    """Apply threshold logic to pick final elements."""
    candidates = sorted(
        [t for t, s in scores.items() if s >= thresh_primary],
        key=scores.get,
        reverse=True,
    )

    # VALID DUAL TYPING
    if len(candidates) >= 2 and scores[candidates[1]] >= thresh_secondary:
        return tuple(candidates[:2])

    # NO VALID CANDIDATES
    elif not candidates:
        return (types.VibemonTypeT.NORMAL,)

    # VALID SINGLE TYPING
    else:
        return tuple(candidates[:1])
