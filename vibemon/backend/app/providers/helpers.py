from typing import Literal
import math
import random

import pydantic
import structlog

from app.core.math import clamp, weighted_sample
from app.core.types import UnitIntervalT
from app.domains.move.catalog import get_move_assignment_bonus
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT

_LOGGER = structlog.get_logger(__name__)

# Floor for move-assignment sampling weights, relative to the max possible weight of
# 2.0 (peak-normalized score x same-type bonus). Keeps unranked move types possible
# without letting their combined mass grow with catalog size.
_MOVE_ASSIGNMENT_WEIGHT_FLOOR = 0.01
_STARTER_MOVE_WEIGHT_FLOOR = _MOVE_ASSIGNMENT_WEIGHT_FLOOR


class Signal(pydantic.BaseModel):
    """Apply binding to raw data."""

    name: str
    attr: str
    raw: float
    min: float
    med: float
    max: float
    axis: Literal["linear", "log10"] = "linear"

    @pydantic.model_validator(mode="after")
    def validate_range(self):
        if not (self.min < self.med < self.max):
            raise ValueError("Must satisfy: min < med < max")
        if self.axis == "log10" and self.min <= 0:
            raise ValueError("axis='log10' requires min > 0")
        return self

    @pydantic.computed_field
    @property
    def clamped(self) -> float:
        """Transform the .raw value to the Signal's basis."""
        return clamp(self.raw, minimum=self.min, maximum=self.max)

    def _inverse_lerp(self, value: float) -> UnitIntervalT:
        """Where ``value`` sits between min and max as a 0-1 fraction (linear or log-spaced)."""
        value = clamp(value, minimum=self.min, maximum=self.max)
        if self.axis == "log10":
            lo = math.log10(self.min)
            hi = math.log10(self.max)
            return (math.log10(value) - lo) / (hi - lo)
        return (value - self.min) / (self.max - self.min)

    @pydantic.computed_field
    @property
    def normal(self) -> UnitIntervalT:
        """
        The signal's value as a percentage (0.0 to 1.0) of its defined range.

        Values below 'min' become 0.0; values above 'max' become 1.0.
        """
        return self._inverse_lerp(self.clamped)

    @pydantic.computed_field
    @property
    def center(self) -> UnitIntervalT:
        """
        Zero-median-anchored normalization: median → 0.5.

        Each half of the population is spread independently across [0, 0.5] or
        (0.5, 1.0] so the median always maps to 0.5 regardless of skew.
        """
        if self.axis == "log10":
            if self.clamped <= self.med:
                lo = math.log10(self.min)
                mid = math.log10(self.med)
                return 0.5 * (math.log10(self.clamped) - lo) / (mid - lo)
            mid = math.log10(self.med)
            hi = math.log10(self.max)
            return 0.5 + 0.5 * (math.log10(self.clamped) - mid) / (hi - mid)

        if self.clamped <= self.med:
            return 0.5 * (self.clamped - self.min) / (self.med - self.min)
        return 0.5 + 0.5 * (self.clamped - self.med) / (self.max - self.med)

    @classmethod
    def mix(
        cls,
        *pairs: tuple[Signal, float],
        mode: Literal["normal", "center"] = "normal",
    ) -> UnitIntervalT:
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
        return clamp(weighted_sum / divisor, minimum=0, maximum=1)

    def __mul__(self, weight: float) -> tuple[Signal, float]:
        """Syntactic sugar for signal.weighted(weight). Enables: signal * 0.5"""
        return self.weighted(weight)

    def __rmul__(self, weight: float) -> tuple[Signal, float]:
        """Syntactic sugar for weight * signal. Enables: 0.5 * signal"""
        return self.weighted(weight)

    def __pow__(self, power: float) -> UnitIntervalT:
        """Syntactic sugar for signal.reshape(power). Enables: signal ** 2"""
        return self.reshape(power)

    def reshape(self, power: float) -> UnitIntervalT:
        """
        Adjusts the sensitivity of the signal using a power curve.

        - power < 1.0: "Aggressive" — Makes low values rise faster.
        - power > 1.0: "Conservative" — Requires higher values before the score rises.
        - power = 1.0: "Linear" — No change.
        """
        return self.normal**power

    def weighted(self, factor: float) -> tuple[Signal, float]:
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
    ) -> UnitIntervalT:
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

        return clamp(v / reach, minimum=0, maximum=1)


def move_assignment_weight(
    move: Move,
    *,
    rankings: dict[VibemonTypeT, float],
    elements: tuple[VibemonTypeT, ...],
    level_weight_exponent: float = 0.0,
) -> float:
    """Relative sampling weight: provider type score x element fit x optional level skew."""
    peak = max(rankings.values(), default=0.0)
    normalized = {element: score / peak for element, score in rankings.items()} if peak > 0 else {}
    type_weight = max(
        normalized.get(move.type, 0.0) * get_move_assignment_bonus(move.type, vibemon_elements=elements),
        _MOVE_ASSIGNMENT_WEIGHT_FLOOR,
    )
    if level_weight_exponent <= 0:
        return type_weight
    return type_weight * max(1.0, move.level_requirement**level_weight_exponent)


def pick_starter_moves(
    *,
    moves: tuple[Move, ...],
    rankings: dict[VibemonTypeT, float],
    elements: tuple[VibemonTypeT, ...],
    k: int,
    rng: random.Random,
) -> list[Move]:
    """
    Select exactly `k` starter moves from a provider's eligible move catalog.

    Sampling is weighted and without replacement. The result always includes
    at least one damaging move; remaining slots are filled from the rest of
    the candidate pool.

    Candidate moves are level-1 moves. Each candidate receives a relative
    sampling weight:

        provider score for the move's type * assignment bonus for the Vibemon's elements

    Rankings are peak-normalized first so providers with different score scales
    (climate ramps vs biome lookup sums) get the same same-type:antagonistic odds.
    The provider score makes moves matching the strongest provider signals more
    likely; the assignment bonus favors same-type and useful coverage moves for the
    already-selected Vibemon `elements`. A small floor keeps unranked move types
    possible-but-rare regardless of catalog size.
    """
    if k <= 0:
        raise ValueError(f"k must be greater than 0, got {k}")

    candidates = tuple(move for move in moves if move.level_requirement == 1)

    if len(candidates) < k:
        raise ValueError(f"Cannot select {k} starter moves from {len(candidates)} eligible starter moves")

    weighted = [
        (move, move_assignment_weight(move, rankings=rankings, elements=elements))
        for move in candidates
    ]
    damaging = [(move, weight) for move, weight in weighted if move.deals_damage]

    if not damaging:
        raise ValueError(
            "Cannot select starter moveset without at least one damaging move "
            f"from {len(candidates)} eligible starter moves"
        )

    first = weighted_sample(
        [move for move, _ in damaging],
        [weight for _, weight in damaging],
        k=1,
        rng=rng,
    )[0]

    remaining = [(move, weight) for move, weight in weighted if move != first]
    if k == 1:
        return [first]

    return [
        first,
        *weighted_sample(
            [move for move, _ in remaining],
            [weight for _, weight in remaining],
            k=k - 1,
            rng=rng,
        ),
    ]
