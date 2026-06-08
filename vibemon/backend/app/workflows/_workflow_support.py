"""Shared helpers for headless Vibemon app workflows."""

import datetime as dt
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import TrainerIdT
from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.encounter import tuning as encounter_tuning
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.schema import PublicVibemon
from app.providers import schema as providers_schema
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import mapper, models, read_model, repositories
from app.storage.secrets.repository import DbTrainerSecrets
from app.workflows.materialize_vibemon import MaterializeVibemon


async def public_vibemon(
    row: models.Vibemon,
    *,
    reviewing_trainer_id: TrainerIdT | None = None,
) -> PublicVibemon:
    assembler = read_model.ReadModelAssembler(
        schema_loader=mapper.vibemon_from_row,
        asset_urler=_default_asset_urler,
    )
    return await assembler.assemble(row, reviewing_trainer_id=reviewing_trainer_id)


async def _default_asset_urler(key: str, expires_in: dt.timedelta) -> str:
    return await get_default_monstore().url(key, expires_in)


async def birth_and_persist_vibemon(
    sess: AsyncSession,
    *,
    birth_seed: BirthSeed,
    nickname: str | None,
    core_identity: str | None,
    now: dt.datetime,
    christen: bool,
) -> tuple[models.Vibemon, tuple[providers_schema.ProviderNote, ...]]:
    snapshot = await birth_seed.fetch_snapshot(DbTrainerSecrets(sess))
    affinities = list(await snapshot.regenerate(birth_seed.providers, birth_seed))
    notes = Affinity.collect_notes(*affinities)
    vibemon = Vibemon.birth(
        *affinities,
        birth_seed=birth_seed,
        nickname=nickname,
        core_identity=core_identity,
    )
    if christen:
        vibemon = await MaterializeVibemon().christen(vibemon)
    row = await repositories.persist_new_vibemon(
        sess,
        vibemon=vibemon,
        birth_seed=birth_seed,
        snapshot=snapshot,
        now=now,
    )
    return row, notes


async def resolve_candidate_to_wild(
    sess: AsyncSession,
    review: models.CandidateReview,
    now: dt.datetime,
    *,
    status: CandidateReviewStatusT,
    event: VibemonHistoryEventT,
) -> None:
    review.status = status.value
    review.resolution = status.value
    review.resolved_at = now
    mark_wild(review.vibemon, now)
    await upsert_encounter_adjustment(sess, review.trainer_id, review.vibemon_id, status.value, now)
    repositories.add_history(sess, review.vibemon_id, event, now, {"trainer_id": str(review.trainer_id)})


def mark_wild(row: models.Vibemon, now: dt.datetime) -> None:
    row.trainer_id = None
    row.crew_slot = None
    row.disposition = VibemonDispositionT.WILD.value
    row.wild_entered_at = now
    row.last_encountered_at = now


def release_to_wild(
    sess: AsyncSession,
    row: models.Vibemon,
    trainer_id: TrainerIdT,
    now: dt.datetime,
) -> None:
    mark_wild(row, now)
    repositories.add_history(sess, row.id, VibemonHistoryEventT.RELEASED, now, {"trainer_id": str(trainer_id)})


async def upsert_encounter_adjustment(
    sess: AsyncSession,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    source: str,
    now: dt.datetime,
) -> None:
    multiplier = encounter_tuning.ADJUSTMENT_MULTIPLIER_BY_SOURCE.get(source)
    if multiplier is None:
        raise ValueError(f"Unknown encounter adjustment source: {source}")
    ends_at = now + encounter_tuning.cooldown_duration(random.Random())
    await repositories.upsert_encounter_adjustment(
        sess,
        trainer_id=trainer_id,
        vibemon_id=vibemon_id,
        source=source,
        multiplier=multiplier,
        starts_at=now,
        ends_at=ends_at,
    )
