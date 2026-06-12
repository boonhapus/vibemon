"""Trainer third-party link persistence."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.trainer import types as trainer_types
from app.storage.database import models
from app.storage.secrets import repository as secrets_repository


async def set_trainer_lastfm_link(
    sess: AsyncSession,
    trainer_id: uuid.UUID,
    *,
    session_key: str | None,
    username: str | None,
) -> None:
    row = await sess.get(models.Trainer, trainer_id)
    if row is None:
        raise ValueError(f"Trainer {trainer_id} does not exist.")
    await secrets_repository.set_trainer_secret(sess, trainer_id, trainer_types.LASTFM_SESSION_KEY, session_key)
    await secrets_repository.set_trainer_secret(sess, trainer_id, trainer_types.LASTFM_USERNAME, username)


async def get_trainer_lastfm_link(sess: AsyncSession, trainer_id: uuid.UUID) -> tuple[str | None, str | None]:
    row = await sess.get(models.Trainer, trainer_id)
    if row is None:
        raise ValueError(f"Trainer {trainer_id} does not exist.")
    session_key = await secrets_repository.get_trainer_secret(sess, trainer_id, trainer_types.LASTFM_SESSION_KEY)
    username = await secrets_repository.get_trainer_secret(sess, trainer_id, trainer_types.LASTFM_USERNAME)
    return session_key, username
