import pytest
import sqlalchemy as sa

from app.domains.trainer import assets as trainer_assets
from app.domains.trainer import const as trainer_const
from app.domains.vibemon.assets import ASSET_VERSION
from app.storage.blob.monstore import MonStore
from app.storage.bootstrap import (
    load_canonical_trainer_display_png,
    load_canonical_trainer_raw_png,
    seed_canonical_trainer,
)
from app.storage.database import models


@pytest.mark.asyncio
async def test_seed_canonical_trainer_writes_trainer_row_and_monstore_blob(sess) -> None:
    monstore = MonStore("memory://")
    raw_bytes = load_canonical_trainer_raw_png()
    display_bytes = load_canonical_trainer_display_png()

    created = await seed_canonical_trainer(sess, monstore=monstore)
    assert created is True

    trainer = await sess.get(models.Trainer, trainer_const.CANONICAL_TRAINER_ID)
    assert trainer is not None
    assert trainer.username == trainer_const.CANONICAL_TRAINER_USERNAME
    assert trainer.reference_detected_facing == "LEFT"

    rows = (
        (
            await sess.execute(
                sa.select(models.TrainerAsset).where(
                    models.TrainerAsset.trainer_id == trainer_const.CANONICAL_TRAINER_ID,
                )
            )
        )
        .scalars()
        .all()
    )
    rows_by_kind = {row.kind: row for row in rows}
    display_row = rows_by_kind[trainer_assets.TrainerAssetKind.REFERENCE.value]
    raw_row = rows_by_kind[trainer_assets.TrainerAssetKind.REFERENCE_RAW.value]

    display_key = f"trainers/{trainer_const.CANONICAL_TRAINER_ID}/{ASSET_VERSION}/r1/sprite/reference.png"
    raw_key = f"trainers/{trainer_const.CANONICAL_TRAINER_ID}/{ASSET_VERSION}/r1/sprite/reference-raw.png"
    assert display_row.object_key == display_key
    assert raw_row.object_key == raw_key
    assert display_row.byte_size == len(display_bytes)
    assert raw_row.byte_size == len(raw_bytes)
    assert await monstore.get(display_key) == display_bytes
    assert await monstore.get(raw_key) == raw_bytes


@pytest.mark.asyncio
async def test_seed_canonical_trainer_is_idempotent(sess) -> None:
    monstore = MonStore("memory://")

    assert await seed_canonical_trainer(sess, monstore=monstore) is True
    assert await seed_canonical_trainer(sess, monstore=monstore) is False

    rows = (
        (
            await sess.execute(
                sa.select(models.TrainerAsset).where(
                    models.TrainerAsset.trainer_id == trainer_const.CANONICAL_TRAINER_ID
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 2
