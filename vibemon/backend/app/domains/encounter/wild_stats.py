"""Aggregate nearby Wild pool statistics for scouting UI."""

from collections import Counter

from app.core.schema import Schema


class WildTypeCount(Schema):
    type: str
    count: int


class WildLevelBucket(Schema):
    label: str
    count: int


class WildStatsRead(Schema):
    count: int
    by_type: list[WildTypeCount]
    level_buckets: list[WildLevelBucket]


def level_bucket_label(level: int) -> str:
    if level <= 5:
        return "1-5"
    if level <= 10:
        return "6-10"
    if level <= 15:
        return "11-15"
    if level <= 20:
        return "16-20"
    return "21+"


def build_wild_stats(rows: list[tuple[int, list[str]]]) -> WildStatsRead:
    type_counts: Counter[str] = Counter()
    level_counts: Counter[str] = Counter()

    for level, elements in rows:
        level_counts[level_bucket_label(level)] += 1
        for element in elements:
            type_counts[str(element)] += 1

    return WildStatsRead(
        count=len(rows),
        by_type=[WildTypeCount(type=type_name, count=count) for type_name, count in type_counts.most_common()],
        level_buckets=[
            WildLevelBucket(label=label, count=level_counts[label])
            for label in ("1-5", "6-10", "11-15", "16-20", "21+")
            if level_counts[label] > 0
        ],
    )
