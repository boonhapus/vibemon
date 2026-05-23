"""Provider move-catalog persistence helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app import models, schema
from app.content import load_universal_moves
from app.plugins.provider import VibeProvider


def _payload_from_move(move: schema.Move) -> dict[str, Any]:
    return {
        "content_id": move.id,
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


def _payload_from_row(row: models.Move) -> dict[str, Any]:
    return {
        "content_id": row.content_id,
        "flavor_text": row.flavor_text,
        "type": row.type,
        "category": row.category,
        "power": row.power,
        "accuracy": row.accuracy,
        "pp": row.pp,
        "priority": row.priority,
        "target": row.target,
        "level_requirement": row.level_requirement,
        "effects": row.effects or [],
        "behavior": row.behavior or {},
    }


def _apply_payload(row: models.Move, payload: dict[str, Any]) -> None:
    row.content_id = payload["content_id"]
    row.flavor_text = payload["flavor_text"]
    row.type = payload["type"]
    row.category = payload["category"]
    row.power = payload["power"]
    row.accuracy = payload["accuracy"]
    row.pp = payload["pp"]
    row.priority = payload["priority"]
    row.target = payload["target"]
    row.level_requirement = payload["level_requirement"]
    row.effects = payload["effects"]
    row.behavior = payload["behavior"]


def upsert_move(
    move: schema.Move,
    cache: dict[str, models.Move],
) -> tuple[models.Move, bool, bool]:
    """Upsert one move by stable content id into an in-memory cache.

    Returns ``(row, created, updated)``.
    """
    payload = _payload_from_move(move)
    if move.id is None:
        raise ValueError(f"Move {move.name!r} has no stable content id.")
    if (existing := cache.get(move.id)) is None:
        row = models.Move(name=move.name, **payload)
        cache[row.content_id] = row
        return row, True, False

    if existing.name != move.name or _payload_from_row(existing) != payload:
        existing.name = move.name
        _apply_payload(existing, payload)
        return existing, False, True

    return existing, False, False


async def load_move_cache(sess: AsyncSession) -> dict[str, models.Move]:
    """Load all persisted move rows keyed by stable content id."""
    return {m.content_id: m for m in (await sess.execute(sa.select(models.Move))).scalars()}


def validate_move_catalog(moves: Iterable[schema.Move]) -> None:
    """Reject move identity or canonical-name collisions before persistence."""
    ids: dict[str, str] = {}
    names: dict[str, str] = {}
    for move in moves:
        if move.id is None:
            raise ValueError(f"Move {move.name!r} has no stable content id.")
        schema.validate_move_id(move.id)
        if (existing_name := ids.get(move.id)) is not None:
            raise ValueError(f"Duplicate move id={move.id!r} for {existing_name!r} and {move.name!r}")
        ids[move.id] = move.name

        canonical_name = move.canonical_name
        if (existing_id := names.get(canonical_name)) is not None:
            raise ValueError(
                f"Duplicate move name={move.name!r} collides with move id={existing_id!r} "
                f"on canonical key={canonical_name!r}"
            )
        names[canonical_name] = move.id


async def sync_provider_moves(
    sess: AsyncSession,
    providers: Iterable[VibeProvider],
    *,
    cache: dict[str, models.Move] | None = None,
) -> tuple[int, int]:
    """Upsert every provider move into ``models.Move``.

    Move ids and canonical move names are globally unique.
    Returns ``(created, updated)``.
    """
    if cache is None:
        cache = await load_move_cache(sess)

    provider_moves = [move for provider in providers for move in provider.moves()]
    provider_moves.extend(load_universal_moves())
    validate_move_catalog(provider_moves)

    existing_names = {schema.canonicalize_move_name(row.name): row.content_id for row in cache.values()}
    created = 0
    updated = 0

    for move in provider_moves:
        assert move.id is not None
        canonical_name = move.canonical_name
        if (existing_id := existing_names.get(canonical_name)) is not None and existing_id != move.id:
            raise ValueError(f"Move catalog conflict for canonical name={canonical_name!r}")
        existing_names[canonical_name] = move.id

        row, was_created, was_updated = upsert_move(move, cache)
        if was_created:
            sess.add(row)
            created += 1
        elif was_updated:
            updated += 1

    return created, updated
