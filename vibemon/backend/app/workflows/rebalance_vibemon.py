"""Replay persisted Vibemon births through current provider balance logic."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.schema import FrozenSchema
from app.domains.generation import snapshot as generation_snapshot
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.identity import Identity
from app.providers.climate.provider import ClimateProvider
from app.storage.database import mapper, models, move_catalog


class RebalanceSummary(FrozenSchema):
    vibemon_id: uuid.UUID
    name: str
    before_identity: Identity
    after_identity: Identity
    before_moves_full: tuple[Move, ...]
    after_moves_full: tuple[Move, ...]
    before_elements: tuple[VibemonTypeT, ...]
    after_elements: tuple[VibemonTypeT, ...]
    before_bst: int
    after_bst: int
    bst_delta: int
    before_moves: tuple[str, ...]
    after_moves: tuple[str, ...]
    type_changed: bool
    stats_changed: bool
    move_definitions_changed: bool
    moves_changed: bool
    changed: bool


async def rebalance_existing_vibemons(
    sess: AsyncSession,
    *,
    vibemon_id: uuid.UUID | None = None,
    limit: int | None = None,
    dry_run: bool = True,
    providers: Iterable[Any] | None = None,
) -> tuple[RebalanceSummary, ...]:
    """Rebuild existing Vibemon identity and moves from stored birth snapshots."""
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    provider_list = tuple(providers or (ClimateProvider(),))
    rows = await _load_rebalance_rows(sess, vibemon_id=vibemon_id, limit=limit)
    summaries: list[RebalanceSummary] = []
    for row in rows:
        summaries.append(await _rebalance_row(sess, row, providers=provider_list, dry_run=dry_run))
    await sess.flush()
    return tuple(summaries)


async def _load_rebalance_rows(
    sess: AsyncSession,
    *,
    vibemon_id: uuid.UUID | None,
    limit: int | None,
) -> list[models.Vibemon]:
    stmt = (
        sa.select(models.Vibemon)
        .options(
            selectinload(models.Vibemon.identity),
            selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
            selectinload(models.Vibemon.assets),
            selectinload(models.Vibemon.birth_snapshot).selectinload(models.BirthSnapshot.birth_seed),
        )
        .order_by(models.Vibemon.id)
    )
    if vibemon_id is not None:
        stmt = stmt.where(models.Vibemon.id == vibemon_id)
    elif limit is not None:
        stmt = stmt.limit(limit)
    return list((await sess.execute(stmt)).scalars())


async def _rebalance_row(
    sess: AsyncSession,
    row: models.Vibemon,
    *,
    providers: tuple[Any, ...],
    dry_run: bool,
) -> RebalanceSummary:
    before = await mapper.vibemon_from_row(row)
    after = await _replay_vibemon(row, providers=providers, before=before)
    summary = _summarize(before, after)
    if not dry_run and summary.changed:
        _apply_identity(row.identity, after.identity)
        await _replace_moves(sess, row, after.moves)
    return summary


async def _replay_vibemon(
    row: models.Vibemon,
    *,
    providers: tuple[Any, ...],
    before: Vibemon,
) -> Vibemon:
    seed_row = row.birth_snapshot.birth_seed
    seed = BirthSeed(
        timestamp=seed_row.timestamp,
        geo_coords=tuple(seed_row.geo_coords),
        providers=list(providers),
    )
    snapshot = generation_snapshot.BirthSnapshot(provider_payloads=row.birth_snapshot.provider_payloads)
    affinities = await snapshot.regenerate(seed.providers, seed)
    vibemon = Vibemon.rebirth(
        *affinities,
        id=row.id,
        name=row.identity.name,
        birth_seed=seed,
        core_identity=row.identity.visual_notes,
        nickname=row.nickname,
        level=row.level,
        xp=row.xp,
        evo_stage=before.evo_stage,
    )
    vibemon.lifecycle = before.lifecycle
    vibemon.trainer_id = before.trainer_id
    vibemon.team_slot = before.team_slot
    vibemon.identity = vibemon.identity.model_copy(
        update={
            "generation": row.identity.generation,
            "generated_at": row.identity.generated_at,
        }
    )
    return vibemon


def _summarize(before: Vibemon, after: Vibemon) -> RebalanceSummary:
    type_changed = before.identity.elements != after.identity.elements
    stats_changed = _stats(before.identity) != _stats(after.identity)
    move_definitions_changed = _move_fingerprints(before.moves) != _move_fingerprints(after.moves)
    moves_changed = _move_ids(before.moves) != _move_ids(after.moves) or move_definitions_changed
    return RebalanceSummary(
        vibemon_id=before.id,
        name=before.identity.name,
        before_identity=before.identity,
        after_identity=after.identity,
        before_moves_full=before.moves,
        after_moves_full=after.moves,
        before_elements=before.identity.elements,
        after_elements=after.identity.elements,
        before_bst=before.identity.bst,
        after_bst=after.identity.bst,
        bst_delta=after.identity.bst - before.identity.bst,
        before_moves=_move_ids(before.moves),
        after_moves=_move_ids(after.moves),
        type_changed=type_changed,
        stats_changed=stats_changed,
        move_definitions_changed=move_definitions_changed,
        moves_changed=moves_changed,
        changed=type_changed or stats_changed or moves_changed,
    )


def _stats(identity: Identity) -> tuple[int, int, int, int, int, int]:
    return (
        identity.base_hp,
        identity.base_attack,
        identity.base_defense,
        identity.base_sp_attack,
        identity.base_sp_defense,
        identity.base_speed,
    )


def _move_ids(moves: tuple[Move, ...]) -> tuple[str, ...]:
    return tuple(move.id for move in moves)


def _move_fingerprints(moves: tuple[Move, ...]) -> tuple[str, ...]:
    return tuple(move.model_dump_json() for move in moves)


def _apply_identity(row: models.Identity, identity: Identity) -> None:
    row.name = identity.name
    row.visual_notes = identity.visual_notes
    row.provider_visual_notes = identity.provider_visual_notes
    row.elements = [element.value for element in identity.elements]
    row.base_hp = identity.base_hp
    row.base_attack = identity.base_attack
    row.base_defense = identity.base_defense
    row.base_sp_attack = identity.base_sp_attack
    row.base_sp_defense = identity.base_sp_defense
    row.base_speed = identity.base_speed
    row.evo_seed = int(identity.evo_seed)
    row.is_radiant = identity.is_radiant
    row.generation = identity.generation
    row.generated_at = identity.generated_at


async def _replace_moves(sess: AsyncSession, row: models.Vibemon, moves: tuple[Move, ...]) -> None:
    cache = await move_catalog.load_move_cache(sess)
    for vibemon_move in list(row.moves):
        await sess.delete(vibemon_move)
    row.moves.clear()

    for slot, move in enumerate(moves):
        move_row, created, _ = move_catalog.upsert_move(move, cache)
        if created:
            sess.add(move_row)
            await sess.flush()
        vibemon_move = models.VibemonMove(
            vibemon_id=row.id,
            move_content_id=move_row.content_id,
            active_slot=slot,
            move=move_row,
        )
        row.moves.append(vibemon_move)
        sess.add(vibemon_move)
