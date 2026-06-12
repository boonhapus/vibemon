"""Birth merge rules: fuse per-provider element evidence and pick final typing."""

from app.domains.move.types import VibemonTypeT


def fuse_element_rankings(
    *pairs: tuple[dict[VibemonTypeT, float], float],
) -> dict[VibemonTypeT, float]:
    """
    Fuse per-provider element evidence into one score dict for final typing.

    Each provider's scores are peak-normalized before merge weighting so providers
    with different score scales (climate ramps vs biome lookup sums) contribute
    comparably. Overlapping types accumulate; provider-only types pass through.
    """
    fused: dict[VibemonTypeT, float] = {}

    for rankings, merge_weight in pairs:
        if not rankings or merge_weight <= 0:
            continue

        peak = max(rankings.values())
        if peak <= 0:
            continue

        scale = merge_weight / peak
        for element, score in rankings.items():
            if score <= 0:
                continue
            fused[element] = fused.get(element, 0.0) + score * scale

    return fused


def filter_element_types(
    scores: dict[VibemonTypeT, float],
    thresh_primary: float = 0.20,
    thresh_secondary: float = 0.65,
) -> tuple[VibemonTypeT, ...]:
    """Apply threshold logic to pick final elements.

    Thresholds are relative to max score: primary must be ≥20% of max,
    secondary must be ≥65% of max for dual-typing.
    """
    if not scores:
        return (VibemonTypeT.NORMAL,)

    if (max_score := max(scores.values())) == 0:
        return (VibemonTypeT.NORMAL,)

    candidates = sorted(
        [t for t, s in scores.items() if s >= thresh_primary * max_score],
        key=lambda element: scores[element],
        reverse=True,
    )

    # VALID DUAL TYPING
    if len(candidates) >= 2 and scores[candidates[1]] >= thresh_secondary * max_score:
        return tuple(candidates[:2])

    # NO VALID CANDIDATES
    elif not candidates:
        return (VibemonTypeT.NORMAL,)

    # VALID SINGLE TYPING
    else:
        return tuple(candidates[:1])
