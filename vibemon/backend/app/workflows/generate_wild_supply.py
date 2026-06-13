"""Generate wild Vibemon supply."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import resolve_clock
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.schema import PublicVibemon
from app.storage.database import vibemon_repo
from app.workflows import birth_persist, public_projection


async def generate_wild_supply(
    sess: AsyncSession,
    *,
    birth_seed: BirthSeed,
    nickname: str | None = None,
    christen: bool = False,
) -> PublicVibemon:
    now = resolve_clock()
    row, _provider_warnings = await birth_persist.birth_and_persist_vibemon(
        sess,
        birth_seed=birth_seed,
        nickname=nickname,
        now=now,
        christen=christen,
    )
    row.disposition = VibemonDispositionT.WILD.value
    row.wild_entered_at = now
    row.last_encountered_at = now
    await sess.flush()
    loaded = await vibemon_repo.load_vibemon(sess, row.id)
    return await public_projection.public_vibemon(loaded)
