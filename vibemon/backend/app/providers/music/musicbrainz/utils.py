from collections.abc import Mapping


def build_simple_lucene_query(params: Mapping[str, str | None]) -> str:
    """
    Build a Lucene query for MusicBrainz indexed field searches.

    Supports simple ``field:value`` pairs joined with ``AND``. Intended for
    recording lookup fields such as ``recording`` and ``artist``.
    """
    parts: list[str] = []

    for field, value in params.items():
        if value is None or value == "":
            continue

        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{field}:"{escaped}"')

    return " AND ".join(parts)
