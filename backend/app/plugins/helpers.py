from typing import Literal

import pydantic
import structlog

from app import types, utils

_LOGGER = structlog.get_logger(__name__)


class Signal(pydantic.BaseModel):
    """
    Apply binding to raw data.
    """

    name: str
    attr: str
    raw: float
    min: float
    med: float
    max: float

    @pydantic.model_validator(mode="after")
    def validate_range(self):
        if not (self.min < self.med < self.max):
            raise ValueError("Must satisfy: min < med < max")
        return self

    @pydantic.computed_field
    @property
    def clamped(self) -> float:
        """Transform the .raw value to the Signal's basis."""
        return utils.clamp(self.raw, minimum=self.min, maximum=self.max)

    @pydantic.computed_field
    @property
    def normal(self) -> types.UnitIntervalT:
        """
        The signal's value as a percentage (0.0 to 1.0) of its defined range.

        Values below 'min' become 0.0; values above 'max' become 1.0.
        """
        return (self.clamped - self.min) / (self.max - self.min)

    @pydantic.computed_field
    @property
    def center(self) -> types.UnitIntervalT:
        """
        Zero‑median‑anchored normalization: median → 0.5.

        Each half of the population is spread independently across [0, 0.5] or
        (0.5, 1.0] so the median always maps to 0.5 regardless of skew.
        """
        if self.clamped <= self.med:
            return 0.5 * (self.clamped - self.min) / (self.med - self.min)
        else:
            return 0.5 + 0.5 * (self.clamped - self.med) / (self.max - self.med)

    @classmethod
    def mix(
        cls,
        *pairs: tuple["Signal", float],
        mode: Literal["normal", "center"] = "normal",
    ) -> types.UnitIntervalT:
        """
        Combines multiple signals into a weighted average.

        Each signal is multiplied by its weight, and the final sum is clamped
        between 0 and 1.

        `mode` selects the per-signal projection:
          - "normal": linear (clamped - min) / (max - min). Skewed signals don't
            anchor to 0.5. Use for additive composition where raw spread matters.
          - "center": median-anchored — median signal value maps to 0.5. Use when
            composing with other median-anchored systems (e.g., asymmetric stat
            scaling) so an "average" city produces an "average" stat.

        Example:
            Signal.mix(sunlight * 0.7, humidity * 0.3, mode="center")
        """
        if not pairs:
            return 0.0

        if (divisor := sum(abs(w) for _, w in pairs)) == 0:
            return 0.0

        weighted_sum = sum(getattr(s, mode) * w for s, w in pairs)
        return utils.clamp(weighted_sum / divisor, minimum=0, maximum=1)

    def __mul__(self, weight: float) -> tuple["Signal", float]:
        """Syntactic sugar for signal.scale(weight). Enables: signal * 0.5"""
        return self.scale(weight)

    def __rmul__(self, weight: float) -> tuple["Signal", float]:
        """Syntactic sugar for weight * signal. Enables: 0.5 * signal"""
        return self.scale(weight)

    def __pow__(self, power: float) -> types.UnitIntervalT:
        """Syntactic sugar for signal.reshape(power). Enables: signal ** 2"""
        return self.reshape(power)

    def reshape(self, power: float) -> types.UnitIntervalT:
        """
        Adjusts the sensitivity of the signal using a power curve.

        - power < 1.0: "Aggressive" — Makes low values rise faster.
        - power > 1.0: "Conservative" — Requires higher values before the score rises.
        - power = 1.0: "Linear" — No change.
        """
        return self.normal**power

    def scale(self, factor: float) -> tuple["Signal", float]:
        """
        Pairs this signal with a weight for use in Signal.mix().

        Note: You can use the `*` operator instead for better readability.
        """
        return (self, factor)

    def ramp(
        self,
        source: Literal["N", "R"] = "N",
        *,
        thresh: float,
        reach: float,
        invert: bool = False,
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

        Composition & Inversion Scenarios
        --------------------------------
        Single ramp — one signal cleanly owns the type.
            score = signal.ramp(...)

        max(a, b) — either signal independently sufficient; do not stack
        correlated alternate causes into an outsized score.
            score = max(a.ramp(...), b.ramp(...))

        1.0 - ramp(...) — high raw values suppress the type, but low values
        are not evidence by themselves (inversion rule).
            score = 1.0 - signal.ramp(...)

        1.0 - k * ramp(...) — high raw values partially suppress the type
        without fully vetoing otherwise valid evidence.
            score = 1.0 - 0.5 * signal.ramp(...)

        a * b — `a` is the core signal and `b` is a gate, veto, or
        attenuator that should suppress mismatched conditions.
            score = core.ramp(...) * gate.ramp(...)

        sqrt(a * b) — both signals required, but direct multiplication
        would over-penalize legitimate paired conditions.
            score = (a.ramp(...) * b.ramp(...)) ** 0.5

        ramp(..., invert=True) — low raw values are positive evidence for
        the type (inversion rule).
            score = signal.ramp(..., invert=True)
        """
        if source not in ("R", "N"):
            raise ValueError(f"source must be one of 'R' or 'N', got '{source}'")

        x = self.normal if source == "N" else self.raw
        v = (thresh - x) if invert else (x - thresh)

        if reach == 0:
            return 1.0 if v >= 0 else 0.0

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
