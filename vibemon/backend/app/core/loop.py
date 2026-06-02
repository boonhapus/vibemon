from collections.abc import Callable, Iterable, Iterator


def partition[T](iterable: Iterable[T], predicate: Callable[[T], bool]) -> tuple[list[T], list[T]]:
    """Partition *iterable* into entries where *predicate* is true, then false."""
    trues: list[T] = []
    falses: list[T] = []

    for item in iterable:
        (trues if predicate(item) else falses).append(item)

    return trues, falses


def chunks[T](items: list[T], *, size: int) -> Iterator[list[T]]:
    """Yield successive chunks of *items*, each of length *size* (last may be shorter)."""
    for i in range(0, len(items), size):
        yield items[i : i + size]
