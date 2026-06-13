"""Birth a Vibemon from a seed and persist it with its snapshot."""

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.generation.types import ProviderWarning
from app.domains.vibemon.entity import Vibemon
from app.storage.database import models, vibemon_repo
from app.storage.secrets.repository import DbTrainerSecrets
from app.workflows import asset_realization


async def birth_and_persist_vibemon(
    sess: AsyncSession,
    *,
    birth_seed: BirthSeed,
    nickname: str | None,
    now: dt.datetime,
    christen: bool,
) -> tuple[models.Vibemon, tuple[ProviderWarning, ...]]:
    snapshot = await birth_seed.fetch_snapshot(DbTrainerSecrets(sess))
    affinities = list(await snapshot.regenerate(birth_seed.providers, birth_seed))
    notes = Affinity.collect_notes(*affinities)
    vibemon = Vibemon.birth(
        *affinities,
        birth_seed=birth_seed,
        nickname=nickname,
    )
    if christen:
        vibemon = await asset_realization.christen_vibemon(vibemon)
    row = await vibemon_repo.persist_new_vibemon(
        sess,
        vibemon=vibemon,
        birth_seed=birth_seed,
        snapshot=snapshot,
        now=now,
    )
    return row, notes
