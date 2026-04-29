from dataclasses import dataclass
from collections.abc import Mapping
import random

import structlog

from app.balance.formulas import base_stat_asymmetric_scaling
from app import schema, types


# ── Provider-side vocabulary ──────────────────────────────────────────────

_LOGGER = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class Event:
    """
    A discrete categorical occurrence in the source data.

    `category` is an opaque string the ruleset interprets (e.g. "rain",
    "thunderstorm", "metal", "jazz"). `severity` indexes into the
    ruleset's `severity_scale`; 0 means "no bonus."
    """
    category: str
    severity: int = 0


@dataclass(frozen=True, slots=True)
class Vocabulary:
    """Point-in-time normalized provider data consumed by the identity engine."""

    signals: Mapping[str, float]
    event: Event | None
    intensity: float


# ── Ruleset ───────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ElementRule:
    """
    A single signal-to-element contribution.

    Contribution = max(0, v - floor) / (1 - floor),
    where v is `signals[channel]` (or 1 - that, if `invert`).
    """
    element: types.VibemonTypeT
    channel: str
    floor: float
    invert: bool = False


@dataclass(frozen=True, slots=True)
class Ruleset:
    """
    Domain-specific game logic. Pure data — no methods, no domain code.

    Fields
    ------
    element_rules
        Continuous channel → element contributions.
    event_affinities
        category → list of (element, base_weight). Final bonus =
        base_weight * severity_scale[event.severity].
    severity_scale
        Index → multiplier. severity_scale[0] should be 0.0.
    stat_map
        Identity stat name → signal name.
    visual_notes
        category → descriptive string.
    default_note
        Returned when no event or unmapped category.
    primary_min
        Minimum score to be considered as a primary element.
    secondary_ratio
        Score-of-second / score-of-first threshold for dual typing.
    """
    element_rules: tuple[ElementRule, ...]
    event_affinities: Mapping[str, tuple[tuple[types.VibemonTypeT, float], ...]]
    severity_scale: tuple[float, ...]
    stat_map: Mapping[str, str]
    visual_notes: Mapping[str, str]
    default_note: str
    signal_move_rules: Mapping[str, tuple[tuple[schema.Move, float], ...]]
    event_move_rules: Mapping[str, tuple[tuple[schema.Move, float], ...]]
    move_pool_size: int = 10
    primary_min: float = 0.20
    secondary_ratio: float = 0.75

    def required_signals(self) -> frozenset[str]:
        """All signal names this ruleset references."""
        return frozenset(
            {r.channel for r in self.element_rules}
            | set(self.stat_map.values())
            | set(self.signal_move_rules.keys())
        )


# ── Engine ────────────────────────────────────────────────────────────────

class IdentityEngine:
    """Synthesizes a Vibemon Identity from any (vocabulary, ruleset) pair."""

    def __init__(self, vocabulary: Vocabulary, ruleset: Ruleset) -> None:
        self._vocabulary = vocabulary
        self._ruleset = ruleset
        self._signals = self._normalize_signals(vocabulary.signals)
        self._validate()

    # -- public API --------------------------------------------------------

    def synthesize_identity(self) -> schema.Identity:
        """Build a deterministic identity from normalized signals and event context."""
        return schema.Identity(
            name="__",
            elements=self._pick_elements(self._signals, self._vocabulary.event),
            **{
                stat: base_stat_asymmetric_scaling(self._signals[field], stat)
                for stat, field in self._ruleset.stat_map.items()
            },
        )

    def synthesize_moves(self) -> list[schema.Move]:
        """Sample a move pool from weighted signal and event contributions."""
        weighted_moves: dict[schema.Move, float] = {}
        self._collect_signal_move_weights(weighted_moves)
        self._collect_event_move_weights(weighted_moves, self._vocabulary.event)
        return self._sample_move_pool(weighted_moves)

    def _collect_signal_move_weights(self, weighted_moves: dict[schema.Move, float]) -> None:
        for signal_name, move_rules in self._ruleset.signal_move_rules.items():
            signal_value = self._signals[signal_name]
            self._add_weighted_moves(weighted_moves, move_rules, signal_value)

    def _collect_event_move_weights(
        self,
        weighted_moves: dict[schema.Move, float],
        event: Event | None,
    ) -> None:
        if event is not None:
            severity_multiplier = self._event_severity_multiplier(event)
            event_rules = self._ruleset.event_move_rules.get(event.category)
            if event_rules is None:
                _LOGGER.warning("identity_engine.unrecognized_event_category", category=event.category)
            else:
                self._add_weighted_moves(weighted_moves, event_rules, severity_multiplier)

    def _sample_move_pool(self, weighted_moves: Mapping[schema.Move, float]) -> list[schema.Move]:
        pool = [(move, weight) for move, weight in weighted_moves.items() if weight > 0]
        if not pool:
            raise ValueError("Ruleset produced an empty move pool after filtering non-positive weights.")

        if len(pool) < self._ruleset.move_pool_size:
            _LOGGER.warning(
                "identity_engine.undersized_move_pool",
                available_moves=len(pool),
                move_pool_size=self._ruleset.move_pool_size,
            )

        return random.choices(
            [move for move, _ in pool],
            weights=[weight for _, weight in pool],
            k=self._ruleset.move_pool_size,
        )

    def get_intensity_value(self) -> float:
        """Expose provider-derived intensity score as-is."""
        return self._vocabulary.intensity

    def generate_visual_note(self) -> str:
        """Pick a flavor note from the event category, with a default fallback."""
        if (event := self._vocabulary.event) is None:
            return self._ruleset.default_note
        return self._ruleset.visual_notes.get(event.category, self._ruleset.default_note)

    # -- internals ---------------------------------------------------------

    def _validate(self) -> None:
        """Fail loudly if the ruleset references signals the vocabulary lacks."""
        produced = frozenset(self._signals.keys())
        required = self._ruleset.required_signals()
        if missing := required - produced:
            raise ValueError(
                f"Ruleset references signals not produced by vocabulary: "
                f"{sorted(missing)}. Vocabulary produces: {sorted(produced)}."
            )

        scale = self._ruleset.severity_scale
        if not scale or scale[0] != 0.0:
            raise ValueError("severity_scale must be non-empty and start with 0.0.")
        if self._ruleset.move_pool_size < 1:
            raise ValueError("move_pool_size must be >= 1.")

    def _pick_elements(
        self,
        signals: Mapping[str, float],
        event: Event | None,
    ) -> types.IdentityElementsT:
        scores: dict[types.VibemonTypeT, float] = {t: 0.0 for t in types.VibemonTypeT}

        # Continuous contributions
        for rule in self._ruleset.element_rules:
            val = signals[rule.channel]
            if rule.invert:
                val = 1.0 - val
            if val > rule.floor:
                scores[rule.element] += (val - rule.floor) / (1.0 - rule.floor)

        # Event contribution
        if event is not None:
            multiplier = self._event_severity_multiplier(event)
            for element, weight in self._ruleset.event_affinities.get(event.category, ()):
                scores[element] += weight * multiplier

        # Selection
        candidates = sorted(
            [t for t, s in scores.items() if s >= self._ruleset.primary_min],
            key=scores.get,  # type: ignore[arg-type]
            reverse=True,
        )

        if not candidates:
            return (types.VibemonTypeT.NORMAL,)

        primary = candidates[0]
        if len(candidates) > 1:
            secondary = candidates[1]
            if scores[secondary] >= scores[primary] * self._ruleset.secondary_ratio:
                return (primary, secondary)
        return (primary,)

    def _clamped_severity_index(self, severity: int) -> int:
        return min(max(0, severity), len(self._ruleset.severity_scale) - 1)

    def _event_severity_multiplier(self, event: Event) -> float:
        return self._ruleset.severity_scale[self._clamped_severity_index(event.severity)]

    @staticmethod
    def _add_weighted_moves(
        weighted_moves: dict[schema.Move, float],
        rules: tuple[tuple[schema.Move, float], ...],
        multiplier: float,
    ) -> None:
        for move, base_weight in rules:
            total = base_weight * multiplier
            if total > 0:
                weighted_moves[move] = weighted_moves.get(move, 0.0) + total

    def _normalize_signals(self, signals: Mapping[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for name, value in signals.items():
            clamped = min(1.0, max(0.0, value))
            if clamped != value:
                _LOGGER.warning(
                    "identity_engine.signal_clamped",
                    signal=name,
                    original_value=value,
                    clamped_value=clamped,
                )
            normalized[name] = clamped
        return normalized
