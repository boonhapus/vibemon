"""Vibemon aggregate persistence."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.domains.generation.seed import BirthSeed
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move.entity import Move
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.blob import assets as blob_assets
from app.storage.database import history_repo, mapper, models, move_catalog


async def persist_new_vibemon(
    sess: AsyncSession,
    *,
    vibemon: Vibemon,
    birth_seed: BirthSeed,
    snapshot: BirthSnapshot,
    now: dt.datetime,
) -> models.Vibemon:
    seed = models.BirthSeed(
        timestamp=birth_seed.timestamp,
        geo_coords=list(birth_seed.geo_coords),
        trainer_id=birth_seed.trainer_id,
    )
    snapshot_row = models.BirthSnapshot(birth_seed=seed, provider_payloads=snapshot.provider_payloads)
    row = models.Vibemon(
        id=vibemon.id,
        nickname=vibemon.nickname,
        xp=vibemon.xp,
        level=vibemon.level,
        growth_rate=vibemon.growth_rate.value,
        evo_stage=int(vibemon.evo_stage),
        lifecycle=vibemon.lifecycle.value,
        disposition=None,
        crew_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot_row,
        wild_entered_at=None,
        last_encountered_at=None,
        expired_at=None,
        reference_detected_facing=(
            vibemon.reference_detected_facing.value if vibemon.reference_detected_facing is not None else None
        ),
    )
    row.identity = mapper.identity_row(vibemon)
    sess.add(row)
    await sess.flush()
    await persist_moves(sess, row, vibemon.moves, now=now)
    await persist_assets(sess, vibemon)
    return row


async def persist_moves(
    sess: AsyncSession,
    row: models.Vibemon,
    moves: tuple[Move, ...],
    *,
    now: dt.datetime,
    source: str = "birth",
) -> None:
    cache = await move_catalog.load_move_cache(sess)  # pyrefly: ignore

    for slot, move in enumerate(moves):
        move_row, created, _ = move_catalog.upsert_move(move, cache)  # pyrefly: ignore
        if created:
            sess.add(move_row)
            await sess.flush()
        sess.add(
            models.VibemonMove(
                vibemon_id=row.id,
                move_content_id=move_row.content_id,
                active_slot=slot,
            )
        )
        history_repo.add_history(
            sess,
            row.id,
            VibemonHistoryEventT.MOVE_LEARNED,
            now,
            {
                "level": str(row.level),
                "move_content_id": move_row.content_id,
                "slot": str(slot),
                "source": source,
            },
        )


async def persist_assets(sess: AsyncSession, vibemon: Vibemon) -> None:
    if vibemon.aesthetic is None:
        return
    await blob_assets.persist_vibemon_slots(sess, vibemon.id, vibemon.aesthetic.assets.values())


async def load_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> models.Vibemon:
    return (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(
                selectinload(models.Vibemon.identity),
                selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                selectinload(models.Vibemon.assets),
                selectinload(models.Vibemon.candidate_reviews),
                selectinload(models.Vibemon.birth_snapshot),
            )
            .where(models.Vibemon.id == vibemon_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
