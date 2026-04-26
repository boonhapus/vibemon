import random


def jitter(base_value: int, *, pct: int = 10) -> int:
    """Apply a jitter to the base_stat value."""
    return round(base_value * (1 + random.randint(-pct, pct) / 100))
