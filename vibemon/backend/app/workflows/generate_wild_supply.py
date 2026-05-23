"""Generate wild Vibemon supply."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import resolve_clock
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.schema import PublicVibemon
from app.storage.database import repositories
from app.workflows import _workflow_support as workflows


async def generate_wild_supply(
    sess: AsyncSession,
    *,
    birth_seed: BirthSeed,
    nickname: str | None = None,
    core_identity: str | None = None,
    christen: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    row = await workflows.birth_and_persist_vibemon(
        sess,
        birth_seed=birth_seed,
        nickname=nickname,
        core_identity=core_identity,
        now=now,
        christen=christen,
    )
    row.disposition = VibemonDispositionT.WILD.value
    row.wild_entered_at = now
    row.last_encountered_at = now
    await sess.flush()
    loaded = await repositories.load_vibemon(sess, row.id)
    return await workflows.public_vibemon(loaded)
