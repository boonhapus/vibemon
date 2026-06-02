"""Database-backed persistence helpers for domain Move definitions."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.move.entity import Move, canonicalize_move_name
from app.storage.database import models


@dataclass(slots=True)
class MoveCache:
    by_content_id: dict[str, models.Move]
    by_canonical_name: dict[str, models.Move]


async def load_move_cache(sess: AsyncSession) -> MoveCache:
    rows = (await sess.execute(sa.select(models.Move))).scalars()
    by_content_id: dict[str, models.Move] = {}
    by_canonical_name: dict[str, models.Move] = {}

    for row in rows:
        by_content_id[row.content_id] = row
        by_canonical_name[canonicalize_move_name(row.name)] = row

    return MoveCache(by_content_id=by_content_id, by_canonical_name=by_canonical_name)


def upsert_move(move: Move, cache: MoveCache) -> tuple[models.Move, bool, bool]:
    row = cache.by_content_id.get(move.id)
    existing_name_row = cache.by_canonical_name.get(move.canonical_name)
    if existing_name_row is not None and existing_name_row is not row:
        raise ValueError(f"Move name collides with existing catalog entry: {move.name!r}")

    if row is None:
        row = _move_row(move)
        cache.by_content_id[move.id] = row
        cache.by_canonical_name[move.canonical_name] = row
        return row, True, True

    old_canonical_name = canonicalize_move_name(row.name)
    changed = _apply_move(row, move)
    if old_canonical_name != move.canonical_name:
        cache.by_canonical_name.pop(old_canonical_name, None)
        cache.by_canonical_name[move.canonical_name] = row
    return row, False, changed


def _move_row(move: Move) -> models.Move:
    return models.Move(**_move_values(move))


def _apply_move(row: models.Move, move: Move) -> bool:
    values = _move_values(move)
    changed = False
    for field, value in values.items():
        if getattr(row, field) != value:
            setattr(row, field, value)
            changed = True
    return changed


def _move_values(move: Move) -> dict[str, object]:
    return {
        "content_id": move.id,
        "name": move.name,
        "flavor_text": move.flavor_text,
        "type": move.type.value,
        "category": move.category.value,
        "power": move.power,
        "accuracy": move.accuracy,
        "pp": move.pp,
        "priority": move.priority,
        "target": move.target.value,
        "level_requirement": move.level_requirement,
        "effects": [group.model_dump(mode="json") for group in move.effects],
        "behavior": move.behavior.model_dump(mode="json"),
    }
