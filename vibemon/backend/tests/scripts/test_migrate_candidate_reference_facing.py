import pytest
import sqlalchemy as sa

from app.domains.trainer import const as trainer_const
from app.storage.blob.monstore import MonStore
from app.storage.database import models
from scripts.migrate_candidate_reference_facing import migrate_reference_facing


@pytest.mark.asyncio
async def test_migrate_reference_facing_adds_columns_and_backfills_canonical_trainer(sess) -> None:
    monstore = MonStore("memory://")
    engine = sess.bind
    assert engine is not None

    sess.add(
        models.Trainer(
            id=trainer_const.CANONICAL_TRAINER_ID,
            username=trainer_const.CANONICAL_TRAINER_USERNAME,
        )
    )
    await sess.commit()

    summary = await migrate_reference_facing(engine, monstore=monstore)

    assert summary.trainers_backfilled == 1
    assert summary.vibemons_backfilled == 0
    assert summary.candidate_reviews_backfilled == 0

    trainer = await sess.get(models.Trainer, trainer_const.CANONICAL_TRAINER_ID)
    assert trainer is not None
    assert trainer.reference_detected_facing == "LEFT"

    async with engine.connect() as conn:
        trainer_columns = await conn.run_sync(
            lambda sync_conn: {col["name"] for col in sa.inspect(sync_conn).get_columns("trainer")}
        )
    assert "reference_detected_facing" in trainer_columns
