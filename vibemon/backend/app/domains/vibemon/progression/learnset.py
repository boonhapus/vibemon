"""Birth-provider move pools resolved live from provider catalogs."""

from collections.abc import Sequence
import datetime as dt
import uuid

from app.domains.generation.affinity import Affinity
from app.domains.generation.merge import fuse_element_rankings
from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import LEARNSET_PAYLOAD_KEY, BirthSnapshot
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT
from app.providers import registry as provider_registry


def birth_provider_names(snapshot: BirthSnapshot) -> tuple[str, ...]:
    """Return birth provider ids stored on the snapshot, ignoring legacy learnset payloads."""
    return tuple(key for key in sorted(snapshot.provider_payloads) if key != LEARNSET_PAYLOAD_KEY)


def birth_seed_for_snapshot(
    snapshot: BirthSnapshot,
    *,
    timestamp: dt.datetime,
    geo_coords: tuple[float, float],
    trainer_id: uuid.UUID,
) -> BirthSeed:
    """Rebuild a domain birth seed from persisted snapshot metadata."""
    return BirthSeed(
        timestamp=timestamp,
        geo_coords=geo_coords,
        trainer_id=trainer_id,
        providers=provider_registry.build_provider_instances(birth_provider_names(snapshot)),
    )


async def fused_element_rankings(snapshot: BirthSnapshot, *, birth_seed: BirthSeed) -> dict[VibemonTypeT, float]:
    """Fuse per-provider element evidence the same way birth typing does."""
    affinities = list(await snapshot.regenerate(birth_seed.providers, birth_seed))
    if not affinities:
        return {}
    pairs = [(Affinity._rankings_for_merge(affinity), 1.0) for affinity in affinities]
    return fuse_element_rankings(*pairs)


def moves_for_providers(
    provider_names: Sequence[str],
    *,
    level: int,
) -> tuple[Move, ...]:
    """Resolve the current provider catalog union eligible at ``level``."""
    moves: dict[str, Move] = {}
    for provider_name in sorted(provider_names):
        try:
            provider_cls = provider_registry.get_catalog_provider(provider_name)
        except KeyError:
            continue
        for move in provider_cls.moves_at_level(level=level):
            moves[move.id] = move
    return tuple(moves.values())


def provider_moves_at_level(snapshot: BirthSnapshot, *, level: int) -> tuple[Move, ...]:
    """Birth-provider moves eligible at ``level`` (universal excluded)."""
    return moves_for_providers(birth_provider_names(snapshot), level=level)
