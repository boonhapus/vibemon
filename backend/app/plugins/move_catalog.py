"""Provider move-catalog persistence helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import json

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app import models, schema
from app.plugins.provider import VibeProvider


def _payload_from_move(move: schema.Move) -> dict[str, Any]:
    return {
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
    """Upsert one move by name into an in-memory cache.

    Returns ``(row, created, updated)``.
    """
    payload = _payload_from_move(move)
    if (existing := cache.get(move.name)) is None:
        row = models.Move(name=move.name, **payload)
        cache[row.name] = row
        return row, True, False

    if _payload_from_row(existing) != payload:
        _apply_payload(existing, payload)
        return existing, False, True

    return existing, False, False


async def load_move_cache(sess: AsyncSession) -> dict[str, models.Move]:
    """Load all persisted move rows keyed by name."""
    return {m.name: m for m in (await sess.execute(sa.select(models.Move))).scalars()}


async def sync_provider_moves(
    sess: AsyncSession,
    providers: Iterable[VibeProvider],
    *,
    cache: dict[str, models.Move] | None = None,
) -> tuple[int, int]:
    """Upsert every provider move into ``models.Move``.

    Move names are globally unique. If two providers publish the same move name
    with different payloads, this raises ``ValueError``.
    Returns ``(created, updated)``.
    """
    if cache is None:
        cache = await load_move_cache(sess)

    seen_catalog: dict[str, str] = {}
    created = 0
    updated = 0

    for provider in providers:
        for move in provider.moves():
            signature = json.dumps(_payload_from_move(move), sort_keys=True)
            if (existing_sig := seen_catalog.get(move.name)) is not None:
                if existing_sig != signature:
                    raise ValueError(f"Move catalog conflict for name={move.name!r} across providers")
                continue
            seen_catalog[move.name] = signature

            row, was_created, was_updated = upsert_move(move, cache)
            if was_created:
                sess.add(row)
                created += 1
            elif was_updated:
                updated += 1

    return created, updated
