import asyncio
import functools as ft


def clamp(value: int, *, minimum: int, maximum: int) -> int:
    """Ensure value is between minimum and maximum."""
    return max(minimum, min(maximum, value))


def _syncify(f):
    """Convert an async function in a sync one."""

    @ft.wraps(f)
    def wrapper(*a, **kw):
        """Run the inner function"""
        return asyncio.run(f(*a, **kw))

    return wrapper
