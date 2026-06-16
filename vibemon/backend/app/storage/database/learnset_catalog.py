"""Load materialized learnset moves from durable catalog storage."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.vibemon.progression import learnset
from app.storage.database import mapper, move_catalog


async def moves_at_level(
    sess: AsyncSession,
    snapshot: BirthSnapshot,
    *,
    level: int,
) -> tuple[Move, ...]:
    """Resolve learnset entries to catalog Move objects eligible at ``level``."""
    entries = learnset.learnset_entries(snapshot)
    if not entries:
        return ()
    cache = await move_catalog.load_move_cache(sess)  # pyrefly: ignore
    moves: list[Move] = []
    for entry in entries:
        if entry.level_requirement > level:
            continue
        row = cache.get(entry.content_id)
        if row is None:
            continue
        moves.append(mapper.move_from_row(row))
    return tuple(moves)
