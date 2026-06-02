import difflib
import functools as ft
import json
import pathlib
import re

from app.domains.move.types import VibemonTypeT

from .lastfm import schema as lastfm_schema
from .musicbrainz import schema as mb_schema

ClassifyRuleT = tuple[str, list[tuple[VibemonTypeT, float]], re.Pattern[str]]


def normalize_string(s: str) -> str:
    """Fold a string."""
    return s.casefold().strip()


def normalize_classify_label(label: str) -> str:
    """Normalize a tag label before classify rule matching."""
    normalized = normalize_string(label)

    while normalized.startswith("#"):
        normalized = normalized.removeprefix("#").strip()

    return normalized


_NON_STUDIO_PATTERN = re.compile(
    r"\b(live|demo|remix|acoustic|instrumental|karaoke|unplugged)\b",
    re.IGNORECASE,
)


def candidate_ranking(
    candidate: mb_schema.Recording, *, track: lastfm_schema.Track
) -> tuple[mb_schema.Recording, float]:
    """Score the similarity between Musicbrainz and LastFM."""
    scores = {
        "title": 0.0,
        "duration": 0.0,
        "artist": 0.0,
    }

    # -- title similarity --

    core = lambda t: re.sub(r"\s*[\(\[].*$", "", t).strip()  # noqa: E731
    a, b = normalize_string(candidate.title), normalize_string(track.name)

    if a == b:
        scores["title"] += 1.0
    elif core(a) and core(a) == core(b):
        scores["title"] += 0.9
    else:
        scores["title"] += difflib.SequenceMatcher(None, a, b).ratio()

    # -- duration similarity --

    tolerance = 3.0  # seconds
    max_delta = 15.0  # seconds
    a, b = candidate.length, track.duration

    if a is None or b is None:
        pass
    elif (delta := (abs(a - b))) <= tolerance:
        scores["duration"] += 1.0
    elif delta >= max_delta:
        pass
    else:
        scores["duration"] += 1.0 - (delta - tolerance) / (max_delta - tolerance)

    # -- artist similarity --

    artists = [c.artist for c in candidate.artist_credit]
    b = normalize_string(track.artist.name)

    if track.artist.mbid is not None and any(a.id == track.artist.mbid for a in artists):
        scores["artist"] += 1.0
    else:
        for artist in artists:
            a = normalize_string(artist.name)

            if a == b:
                scores["artist"] += 0.85
            elif b in a:
                scores["artist"] += 0.60

    # -- final scoring --

    # fmt: off
    score = (
        scores["title"] * 0.4
        + scores["duration"] * 0.35
        + scores["artist"] * 0.25
        + (0.08 if candidate.isrcs else 0)
        - (0.12 if _NON_STUDIO_PATTERN.search(f"{candidate.disambiguation} {candidate.title}") is not None else 0)
    )
    # fmt: on

    return (candidate, min(score, 1.0))


@ft.cache
def load_rules(filename: str) -> tuple[ClassifyRuleT, ...]:
    """Load a rule file from the music/data directory."""
    path = pathlib.Path(__file__).resolve().parent / "data" / filename
    payload = json.loads(path.read_text(encoding="utf-8"))
    rules: list[ClassifyRuleT] = []

    for entry in payload:
        weights = [(VibemonTypeT(element), weight) for element, weight in entry["weights"].items()]

        parts: list[str] = []

        for term in entry.get("terms", []):
            parts.append(rf"\b{re.escape(term)}\b")

        for pattern in entry.get("patterns", []):
            parts.append(pattern)

        if not parts:
            raise ValueError(f"classify rule {entry.get('name', '<unknown>')!r} needs terms and/or patterns")

        rules.append((entry["name"], weights, re.compile("|".join(parts), re.I)))

    return tuple(rules)
