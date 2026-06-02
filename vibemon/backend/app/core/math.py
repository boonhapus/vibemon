"""Small numeric helpers shared by providers and domain formulas."""

from collections.abc import Iterable
import random


def clamp(value: float, *, minimum: float, maximum: float) -> float:
    """Pin ``value`` to the inclusive ``[minimum, maximum]`` range."""
    return max(minimum, min(maximum, value))


def weighted_sample[T](
    population: Iterable[T],
    weights: Iterable[float],
    *,
    k: int = 1,
    rng: random.Random | None = None,
) -> list[T]:
    """Sample ``k`` distinct items without replacement, weighted by ``weights``."""
    population = list(population)
    weights = list(weights)

    if len(population) != len(weights):
        raise ValueError("population and weights must have the same length")

    if not (0 < k <= len(population)):
        raise ValueError(f"k must be between 1 and {len(population)}")

    chooser = rng if rng is not None else random
    r: list[T] = []

    for _ in range(k):
        i = chooser.choices(range(len(population)), weights=weights, k=1)[0]
        del weights[i]
        r.append(population.pop(i))

    return r
