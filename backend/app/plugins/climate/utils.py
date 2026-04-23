import random


def jitter(base_value: int) -> int:
    """Apply a jitter to the base_stat value."""
    return round(base_value * (1 + random.randint(-10, 10) / 100))
