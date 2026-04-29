"""
Shared optional helpers for VibeProvider implementations.

Eliminates the need for engine.py, Ruleset, Vocabulary, and Event abstractions.
Providers use these utilities directly in their synthesize() method.
"""
from typing import Callable, Mapping
import random
import structlog

from app import schema, types
from app.balance.formulas import base_stat_asymmetric_scaling


_LOGGER = structlog.get_logger(__name__)

# ── Types ───────────────────────────────────────────────────────────────────

ElementScoreCallback = Callable[[Mapping[str, float]], float]
"""Takes dict of normalized signal values (0-1), returns element score (0-1+)."""


# ── Normalization ──────────────────────────────────────────────────────────

def normalize(value: float, low: float, high: float) -> float:
    """Map raw value to 0-1 range, clamped to [0.0, 1.0]."""
    if high <= low:
        _LOGGER.warning("helpers.normalize_invalid_bounds", low=low, high=high)
        return 0.5
    ratio = (value - low) / (high - low)
    return max(0.0, min(1.0, ratio))


# ── Element Selection ──────────────────────────────────────────────────────

def build_element_scores(
    data: Mapping[str, float],
    callbacks: Mapping[types.VibemonTypeT, ElementScoreCallback],
) -> dict[types.VibemonTypeT, float]:
    """
    Run all callbacks to build element score dict.

    Args:
        data: Normalized signal values (0-1), keyed by signal name.
        callbacks: Map of element → callback that returns its score.

    Returns:
        Dict of {element: score} with all scores >= 0.
    """
    scores: dict[types.VibemonTypeT, float] = {}
    for element, callback in callbacks.items():
        try:
            score = callback(data)
            if score > 0:
                scores[element] = score
        except Exception as e:
            _LOGGER.warning(
                "helpers.build_element_scores_callback_error",
                element=element,
                error=str(e),
            )
    return scores


def select_elements(
    scores: Mapping[types.VibemonTypeT, float],
    primary_min: float = 0.2,
    secondary_ratio: float = 0.75,
) -> tuple[types.VibemonTypeT, ...]:
    """
    Apply threshold logic to pick final elements.

    Args:
        scores: Dict of {element: score}. Scores below primary_min are ignored.
        primary_min: Minimum score to be considered as a primary element.
        secondary_ratio: Score-of-second / score-of-first threshold for dual typing.

    Returns:
        Tuple of selected elements (1 or 2 elements).
    """
    if not scores:
        return (types.VibemonTypeT.NORMAL,)

    # Filter and sort by score descending
    candidates = sorted(
        [t for t, s in scores.items() if s >= primary_min],
        key=scores.get,
        reverse=True,
    )

    if not candidates:
        return (types.VibemonTypeT.NORMAL,)

    primary = candidates[0]
    if len(candidates) > 1:
        secondary = candidates[1]
        if scores[secondary] >= scores[primary] * secondary_ratio:
            return (primary, secondary)
    return (primary,)


# ── Move Pool Sampling ─────────────────────────────────────────────────────

def sample_move_pool(
    weighted_moves: Mapping[schema.Move, float],
    pool_size: int = 10,
) -> list[schema.Move]:
    """
    Sample weighted moves to final pool.

    Args:
        weighted_moves: Dict of {move: weight}. Weights <= 0 are filtered out.
        pool_size: Number of moves to sample.

    Returns:
        List of sampled moves (may be smaller than pool_size if not enough valid moves).

    Raises:
        ValueError: If no moves have positive weight after filtering.
    """
    pool = [(move, weight) for move, weight in weighted_moves.items() if weight > 0]

    if not pool:
        raise ValueError("No moves with positive weight after filtering.")

    if len(pool) < pool_size:
        _LOGGER.warning(
            "helpers.undersized_move_pool",
            available_moves=len(pool),
            requested_size=pool_size,
        )

    return random.choices(
        [move for move, _ in pool],
        weights=[weight for _, weight in pool],
        k=min(pool_size, len(pool)),
    )


def apply_type_affinity_weights(
    move_weights: Mapping[schema.Move, float],
    elements: tuple[types.VibemonTypeT, ...],
    same_type_bonus: float = 1.5,
    opposite_type_penalty: float = 0.5,
) -> dict[schema.Move, float]:
    """
    Adjust move weights based on elemental type affinity.

    Uses element_chart.py effectiveness logic:
    - Moves matching Vibemon elements get same_type_bonus multiplier (like STAB)
    - Moves of "opposite" types (ineffective vs Vibemon) get opposite_type_penalty

    Args:
        move_weights: Original {move: weight} dict.
        elements: Vibemon's elemental typing.
        same_type_bonus: Multiplier for moves matching Vibemon elements.
        opposite_type_penalty: Multiplier for moves of ineffective types.

    Returns:
        New dict with adjusted weights.
    """
    from app.balance import element_chart

    adjusted: dict[schema.Move, float] = {}
    elements_set = set(elements)

    for move, weight in move_weights.items():
        multiplier = 1.0

        # Same type bonus (STAB-like)
        if move.type in elements_set:
            multiplier = same_type_bonus
        else:
            # Check if move type is ineffective against any of our elements
            # (simplified: if it's resisted by at least one element, consider it "opposite")
            for elem in elements:
                effectiveness = element_chart.get_effectiveness(move.type, elem)
                if effectiveness < 1.0:
                    multiplier = opposite_type_penalty
                    break

        adjusted[move] = weight * multiplier

    return adjusted
