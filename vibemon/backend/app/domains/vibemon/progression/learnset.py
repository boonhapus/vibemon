"""Birth-scoped learnset materialization and snapshot storage."""

from collections.abc import Sequence

from app.core.schema import FrozenSchema
from app.domains.generation.snapshot import BirthSnapshot, LEARNSET_PAYLOAD_KEY
from app.domains.move import universal
from app.domains.move.entity import Move
from app.providers import registry as provider_registry


class LearnsetEntry(FrozenSchema):
    content_id: str
    level_requirement: int


def materialize_learnset(provider_names: Sequence[str]) -> tuple[LearnsetEntry, ...]:
    """Capture the full provider move pool at birth without live Provider instances later."""
    entries: dict[str, LearnsetEntry] = {}
    for move in universal.moves():
        entries[move.id] = LearnsetEntry(content_id=move.id, level_requirement=move.level_requirement)
    for provider_name in sorted(provider_names):
        try:
            provider = provider_registry.get_catalog_provider(provider_name)()
        except KeyError:
            continue
        for move in provider.moves():
            entries[move.id] = LearnsetEntry(content_id=move.id, level_requirement=move.level_requirement)
    return tuple(entries.values())


def materialize_learnset_moves(provider_names: Sequence[str]) -> tuple[Move, ...]:
    """Full Move objects for catalog upsert at birth."""
    moves: dict[str, Move] = {}
    for move in universal.moves():
        moves[move.id] = move
    for provider_name in sorted(provider_names):
        try:
            provider = provider_registry.get_catalog_provider(provider_name)()
        except KeyError:
            continue
        for move in provider.moves():
            moves[move.id] = move
    return tuple(moves.values())


def snapshot_with_learnset(snapshot: BirthSnapshot, entries: tuple[LearnsetEntry, ...]) -> BirthSnapshot:
    payloads = dict(snapshot.provider_payloads)
    payloads[LEARNSET_PAYLOAD_KEY] = {"entries": [entry.model_dump(mode="json") for entry in entries]}
    return BirthSnapshot(provider_payloads=payloads)


def learnset_entries(snapshot: BirthSnapshot) -> tuple[LearnsetEntry, ...]:
    raw = snapshot.provider_payloads.get(LEARNSET_PAYLOAD_KEY)
    if raw is None:
        return ()
    return tuple(LearnsetEntry.model_validate(entry) for entry in raw["entries"])


def birth_provider_names(snapshot: BirthSnapshot) -> tuple[str, ...]:
    return tuple(key for key in sorted(snapshot.provider_payloads) if key != LEARNSET_PAYLOAD_KEY)
