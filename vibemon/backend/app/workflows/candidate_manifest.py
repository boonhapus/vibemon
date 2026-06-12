"""Background-safe manifestation of a freshly adopted Vibemon."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import structlog

from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import mapper, vibemon_repo
from app.workflows import asset_realization

_LOGGER = structlog.get_logger(__name__)


async def manifest_adopted_vibemon(
    vibemon_id: uuid.UUID,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Manifest an owned Vibemon in its own session; safe as a background task."""
    async with session_factory() as sess:
        try:
            row = await vibemon_repo.load_vibemon(sess, vibemon_id)
            vibemon = await mapper.vibemon_from_row(row)
            if vibemon.lifecycle is VibemonLifecycleT.MANIFESTED:
                return
            vibemon = await asset_realization.manifest_vibemon(vibemon)
            mapper.apply_vibemon_to_row(row, vibemon)
            await vibemon_repo.persist_assets(sess, vibemon)
            await sess.commit()
            await _LOGGER.ainfo("background_manifest_complete", vibemon_id=str(vibemon_id))
        except Exception as exc:
            await sess.rollback()
            await _LOGGER.aerror("background_manifest_failed", vibemon_id=str(vibemon_id), error=str(exc))
