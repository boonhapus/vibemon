from typing import Literal

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

    def ramp(
        self,
        source: Literal["N", "R"] = "N",
        *,
        thresh: float,
        reach: float,
        invert: bool = False
    ) -> types.UnitIntervalT:
        """
        Score how strongly this signal activates, as a value in [0, 1].

        The signal is compared against `thresh`; once it crosses, the score
        ramps linearly up to 1.0 over a distance of `reach`.

            score
              1 |          ┌──────
                |         /
                |        /
              0 |───────┘
                └───────┬───┬────── signal
                    thresh thresh+reach

        Use `source` N[ormal] when thresh/reach are easier to reason about as fractions.
        Use `source` R[aw]    when thresh/reach are easier to reason about in real units.

        If `signal` is below the `thresh` (or above, if `invert`ed) then it is
        interpreted as 0.

        `reach` describes how far the signal is must travel to reach 1.

        Three common shapes
        -------------------
        Threshold Ramp — activates only past a cutoff, then ramps to full.
            signal: any , thresh: 0.55 , reach: 0.45
            e.g. "cloud cover above 55% counts, fully cloudy at 100%"

        Inverse Ramp — full score when low, fading out as the signal rises.
            signal: any , thresh: 0.45 , reach: 0.45 , invert: True
            e.g. "no rain gets full credit, fades out by 0.45 mm/day"

        Proportional Ramp — score equals the signal itself (pass-through).
            signal: any , thresh: 0.00 , reach: 1.00
            e.g. "score directly proportional to humidity"
        """
        x = self.normal if source == "N" else self.raw
        v = (thresh - x) if invert else (x - thresh)
        return utils.clamp(v / reach, minimum=0, maximum=1)


def filter_element_types(
    scores: dict[types.VibemonTypeT, float],
    thresh_primary: float = 0.20,
    thresh_secondary: float = 0.65,
) -> tuple[types.VibemonTypeT, ...]:
    """Apply threshold logic to pick final elements.

    Thresholds are relative to max score: primary must be ≥20% of max,
    secondary must be ≥65% of max for dual-typing.
    """
    if not scores:
        return (types.VibemonTypeT.NORMAL,)

    if (max_score := max(scores.values())) == 0:
        return (types.VibemonTypeT.NORMAL,)

    candidates = sorted(
        [t for t, s in scores.items() if s >= thresh_primary * max_score],
        key=scores.get,
        reverse=True,
    )

    # VALID DUAL TYPING
    if len(candidates) >= 2 and scores[candidates[1]] >= thresh_secondary * max_score:
        return tuple(candidates[:2])

    # NO VALID CANDIDATES
    elif not candidates:
        return (types.VibemonTypeT.NORMAL,)

    # VALID SINGLE TYPING
    else:
        return tuple(candidates[:1])
