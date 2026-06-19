"""Persist battle XP, evolution, and move-learning outcomes."""

from typing import Any
import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app.core.errors import BattleUnavailable
from app.core.ids import TrainerIdT
from app.core.time import resolve_clock
from app.domains.battle import entity
from app.domains.generation.snapshot import BirthSnapshot
from app.domains.move import universal
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.progression import engine as progression_engine
from app.domains.vibemon.progression import formulas as progression_formulas
from app.domains.vibemon.progression import learnset
from app.storage.database import history_repo, mapper, models, move_catalog, vibemon_repo


async def persist_battle_progression(
    sess: AsyncSession,
    *,
    battle: entity.Battle,
    battle_id: uuid.UUID,
    now: dt.datetime | None = None,
) -> progression_engine.BattleProgressionResult:
    """Apply XP and progression for all battle participants after conclusion."""
    if not battle.concluded:
        raise BattleUnavailable("Battle is not concluded.")

    occurred_at = now or resolve_clock()
    participant_ids = [combatant.id for trainer in (battle.trainer_a, battle.trainer_b) for combatant in trainer.crew]
    rows = await _load_participant_rows(sess, participant_ids)
    snapshots = {
        row.id: BirthSnapshot(provider_payloads=dict(row.birth_snapshot.provider_payloads)) for row in rows.values()
    }
    auto_evolve_by_id = {row_id: row.disposition == "wild" for row_id, row in rows.items()}
    learned_exclude_by_id: dict[uuid.UUID, set[str]] = {}
    provider_moves_by_id: dict[uuid.UUID, tuple[Any, ...]] = {}
    element_rankings_by_id: dict[uuid.UUID, dict[VibemonTypeT, float]] = {}
    xp_totals = progression_engine.accumulate_battle_xp(battle)
    for combatant in (member for trainer in (battle.trainer_a, battle.trainer_b) for member in trainer.crew):
        snapshot = snapshots[combatant.id]
        row = rows[combatant.id]
        history_events = await history_repo.load_history_events(sess, combatant.id)
        learned_exclude_by_id[combatant.id] = _learned_exclude_ids(history_events)
        xp_gain = xp_totals.get(combatant.id, 0)
        projected_level = progression_formulas.level_from_total_xp(
            combatant.xp + xp_gain,
            growth_rate=combatant.growth_rate,
        )
        provider_moves_by_id[combatant.id] = learnset.provider_moves_at_level(snapshot, level=projected_level)
        birth_seed = learnset.birth_seed_for_snapshot(
            snapshot,
            timestamp=row.birth_snapshot.birth_seed.timestamp,
            geo_coords=tuple(row.birth_snapshot.birth_seed.geo_coords),
            trainer_id=row.birth_snapshot.birth_seed.trainer_id,
        )
        element_rankings_by_id[combatant.id] = await learnset.fused_element_rankings(snapshot, birth_seed=birth_seed)

    result = progression_engine.resolve_battle_progression(
        battle,
        battle_id=battle_id,
        provider_moves_by_id=provider_moves_by_id,
        universal_moves=universal.moves(),
        learned_exclude_by_id=learned_exclude_by_id,
        auto_evolve_by_id=auto_evolve_by_id,
        element_rankings_by_id=element_rankings_by_id,
    )

    for delta in result.deltas:
        row = rows[delta.vibemon_id]
        mapper.apply_vibemon_to_row(row, delta.vibemon)
        if delta.xp_award is not None:
            history_repo.add_history(
                sess,
                delta.vibemon_id,
                VibemonHistoryEventT.BATTLE_RESULT,
                occurred_at,
                {
                    "battle_id": str(battle_id),
                    "xp_gained": str(delta.xp_award.xp_gained),
                    "previous_level": str(delta.xp_award.previous_level),
                    "new_level": str(delta.xp_award.new_level),
                },
            )
            if delta.xp_award.new_level > delta.xp_award.previous_level:
                history_repo.add_history(
                    sess,
                    delta.vibemon_id,
                    VibemonHistoryEventT.LEVEL_UP,
                    occurred_at,
                    {
                        "previous_level": str(delta.xp_award.previous_level),
                        "new_level": str(delta.xp_award.new_level),
                        "source": "battle",
                    },
                )
        if delta.evolution_applied is not None:
            history_repo.add_history(
                sess,
                delta.vibemon_id,
                VibemonHistoryEventT.EVOLUTION,
                occurred_at,
                {
                    "from_stage": str(int(delta.evolution_applied.from_stage)),
                    "to_stage": str(int(delta.evolution_applied.to_stage)),
                    "auto": "true",
                },
            )
        if auto_evolve_by_id.get(delta.vibemon_id, False):
            await _sync_learned_moves(sess, row, delta, occurred_at=occurred_at)

    await sess.flush()
    return result


async def accept_move_learn(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    move_content_id: str,
    pending_offer: progression_engine.MoveLearnOffer,
    replace_content_id: str | None = None,
    now: dt.datetime | None = None,
) -> models.Vibemon:
    """Keep an offered move from the pending battle offer, optionally replacing an active slot."""
    occurred_at = now or resolve_clock()
    row = await _load_owned_row(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    if pending_offer.vibemon_id != vibemon_id:
        raise BattleUnavailable("No pending move offer for that Vibemon.")
    move = next((candidate for candidate in pending_offer.moves if candidate.id == move_content_id), None)
    if move is None:
        raise BattleUnavailable("That move is not in the current offer.")

    known_ids = {active.id for active in vibemon.moves}
    if move.id in known_ids:
        raise BattleUnavailable("This Vibemon already knows that move.")

    if len(vibemon.moves) >= progression_engine.MAX_ACTIVE_MOVES:
        if replace_content_id is None:
            raise BattleUnavailable("Choose a move to replace.")
        if replace_content_id not in known_ids:
            raise BattleUnavailable("Replacement move is not active.")
        replaced_slot = next(index for index, active in enumerate(vibemon.moves) if active.id == replace_content_id)
        forgotten = vibemon.moves[replaced_slot]
        updated_moves = list(vibemon.moves)
        updated_moves[replaced_slot] = move
        vibemon = vibemon.model_copy(update={"moves": tuple(updated_moves)})
        mapper.apply_vibemon_to_row(row, vibemon)
        await _replace_move_row(sess, row, forgotten_id=forgotten.id, move=move, slot=replaced_slot)
        history_repo.add_history(
            sess,
            vibemon_id,
            VibemonHistoryEventT.MOVE_FORGOTTEN,
            occurred_at,
            {"move_content_id": forgotten.id, "reason": "replaced"},
        )
        history_repo.add_history(
            sess,
            vibemon_id,
            VibemonHistoryEventT.MOVE_LEARNED,
            occurred_at,
            {
                "level": str(vibemon.level),
                "move_content_id": move.id,
                "slot": str(replaced_slot),
                "source": "level_up",
                "outcome": "kept",
                "replaced_move_content_id": forgotten.id,
            },
        )
    else:
        slot = len(vibemon.moves)
        vibemon = vibemon.model_copy(update={"moves": (*vibemon.moves, move)})
        mapper.apply_vibemon_to_row(row, vibemon)
        cache = await move_catalog.load_move_cache(sess)  # pyrefly: ignore
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
            vibemon_id,
            VibemonHistoryEventT.MOVE_LEARNED,
            occurred_at,
            {
                "level": str(vibemon.level),
                "move_content_id": move.id,
                "slot": str(slot),
                "source": "level_up",
                "outcome": "kept",
            },
        )

    await sess.flush()
    return row


async def decline_move_learn(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    pending_offer: progression_engine.MoveLearnOffer,
    now: dt.datetime | None = None,
) -> None:
    """Decline a pending four-choice offer without changing active moves.

    No history is recorded — declined moves stay eligible for future offers.
    """
    _ = now or resolve_clock()
    row = await _load_owned_row(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    if pending_offer.vibemon_id != vibemon_id:
        raise BattleUnavailable("No pending move offer for that Vibemon.")
    if row is None:
        raise BattleUnavailable("That Vibemon is not in your crew.")


def _learned_exclude_ids(history_events: tuple[dict[str, object], ...]) -> set[str]:
    from app.domains.vibemon.progression import move_offers

    return move_offers.learned_and_forgotten_ids(history_events)


async def accept_evolution(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    now: dt.datetime | None = None,
) -> models.Vibemon:
    """Promote an owned mon past a pending evolution milestone."""
    occurred_at = now or resolve_clock()
    row = await _load_owned_row(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    pending = progression_formulas.pending_evolution_stage(
        level=vibemon.level,
        growth_rate=vibemon.growth_rate,
        evo_seed=vibemon.identity.evo_seed,
        current_stage=vibemon.evo_stage,
    )
    if pending is None:
        raise BattleUnavailable("This Vibemon has no pending evolution.")
    evolved = progression_engine.apply_evolution(vibemon, to_stage=pending)
    mapper.apply_vibemon_to_row(row, evolved)
    history_repo.add_history(
        sess,
        vibemon_id,
        VibemonHistoryEventT.EVOLUTION,
        occurred_at,
        {
            "from_stage": str(int(vibemon.evo_stage)),
            "to_stage": str(int(pending)),
            "auto": "false",
        },
    )
    await sess.flush()
    return row


async def _load_participant_rows(
    sess: AsyncSession,
    participant_ids: list[uuid.UUID],
) -> dict[uuid.UUID, models.Vibemon]:
    rows = (
        (
            await sess.execute(
                sa.select(models.Vibemon)
                .options(
                    selectinload(models.Vibemon.identity),
                    selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                    selectinload(models.Vibemon.birth_snapshot).selectinload(models.BirthSnapshot.birth_seed),
                )
                .where(models.Vibemon.id.in_(participant_ids))
                .with_for_update()
            )
        )
        .scalars()
        .all()
    )
    return {row.id: row for row in rows}


async def _load_owned_row(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
) -> models.Vibemon:
    row = (
        await sess.execute(
            sa.select(models.Vibemon)
            .options(
                selectinload(models.Vibemon.identity),
                selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                selectinload(models.Vibemon.assets),
                selectinload(models.Vibemon.birth_snapshot).selectinload(models.BirthSnapshot.birth_seed),
            )
            .where(
                models.Vibemon.id == vibemon_id,
                models.Vibemon.trainer_id == trainer_id,
            )
            .with_for_update()
        )
    ).scalar_one_or_none()
    if row is None:
        raise BattleUnavailable("That Vibemon is not in your crew.")
    return row


async def _sync_learned_moves(
    sess: AsyncSession,
    row: models.Vibemon,
    delta: progression_engine.ProgressionDelta,
    *,
    occurred_at: dt.datetime,
) -> None:
    if len(delta.vibemon.moves) <= len(row.moves):
        return
    existing_ids = {link.move_content_id for link in row.moves}
    new_moves = [move for move in delta.vibemon.moves if move.id not in existing_ids]
    if not new_moves:
        return
    await vibemon_repo.persist_moves(sess, row, tuple(new_moves), now=occurred_at, source="level_up")


async def _replace_move_row(
    sess: AsyncSession,
    row: models.Vibemon,
    *,
    forgotten_id: str,
    move: object,
    slot: int,
) -> None:
    cache = await move_catalog.load_move_cache(sess)  # pyrefly: ignore
    move_row, created, _ = move_catalog.upsert_move(move, cache)  # pyrefly: ignore
    if created:
        sess.add(move_row)
        await sess.flush()
    link = next(link for link in row.moves if link.move_content_id == forgotten_id)
    await sess.delete(link)
    sess.add(
        models.VibemonMove(
            vibemon_id=row.id,
            move_content_id=move_row.content_id,
            active_slot=slot,
        )
    )
