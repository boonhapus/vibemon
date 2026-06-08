"""Tests for trainer username database repair."""

import uuid

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.database import models
from app.storage.database import repair as db_repair


async def test_repair_merges_case_insensitive_duplicate_trainers(sess: AsyncSession) -> None:
    keeper_id = uuid.uuid7()
    duplicate_id = uuid.uuid7()
    sess.add(models.Trainer(id=keeper_id, username="Ada"))
    sess.add(models.Trainer(id=duplicate_id, username="ada"))
    await sess.commit()

    await db_repair.repair_trainer_usernames(sess)
    await sess.commit()

    trainers = (await sess.scalars(sa.select(models.Trainer))).all()
    assert len(trainers) == 1
    assert trainers[0].id == keeper_id
    assert trainers[0].username == "ada"
