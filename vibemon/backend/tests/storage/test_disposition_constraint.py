"""Verify ck_vibemon_disposition_shape on SQLite and Postgres."""

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import pytest
import sqlalchemy as sa

from app.storage.database import models


async def _insert_vibemon(
    sess: sa.ext.asyncio.AsyncSession,
    *,
    birth_snapshot_id: uuid.UUID,
    disposition: str | None,
    trainer_id: uuid.UUID | None,
    team_slot: int | None,
    expired_at: dt.datetime | None = None,
) -> uuid.UUID:
    vibemon_id = uuid.uuid7()
    identity_id = uuid.uuid7()
    sess.add(
        models.Identity(
            id=identity_id,
            vibemon_id=vibemon_id,
            name="test",
            elements=["normal"],
            base_hp=1,
            base_attack=1,
            base_defense=1,
            base_sp_attack=1,
            base_sp_defense=1,
            base_speed=1,
            evo_seed=0,
            is_radiant=False,
            generated_at=dt.datetime.now(dt.UTC),
        )
    )
    sess.add(
        models.Vibemon(
            id=vibemon_id,
            nickname=None,
            level=1,
            evo_stage=0,
            lifecycle="schema_ready",
            disposition=disposition,
            team_slot=team_slot,
            trainer_id=trainer_id,
            birth_snapshot_id=birth_snapshot_id,
            wild_entered_at=None,
            last_encountered_at=None,
            expired_at=expired_at,
        )
    )
    await sess.flush()
    return vibemon_id


@pytest.fixture
async def birth_snapshot_id(sess: AsyncSession) -> uuid.UUID:
    trainer_id = uuid.uuid7()
    seed_id = uuid.uuid7()
    snapshot_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"trainer-{trainer_id.hex[:8]}"))
    sess.add(
        models.BirthSeed(
            id=seed_id,
            timestamp=dt.datetime.now(dt.UTC),
            geo_coords=[0.0, 0.0],
            trainer_id=trainer_id,
        )
    )
    sess.add(
        models.BirthSnapshot(
            id=snapshot_id,
            birth_seed_id=seed_id,
            provider_payloads={},
        )
    )
    await sess.flush()
    return snapshot_id


@pytest.fixture
async def trainer_id(sess: AsyncSession, birth_snapshot_id: uuid.UUID) -> uuid.UUID:
    del birth_snapshot_id
    row = (await sess.execute(sa.select(models.Trainer))).scalar_one()
    return row.id


@pytest.mark.parametrize(
    ("disposition", "team_slot", "trainer_id_key", "expired_at"),
    [
        (None, None, None, None),
        ("owned", 0, "trainer", None),
        ("wild", None, None, None),
        ("expired", None, None, dt.datetime.now(dt.UTC)),
    ],
)
@pytest.mark.asyncio
async def test_disposition_constraint_accepts_valid_shapes(
    sess: AsyncSession,
    birth_snapshot_id: uuid.UUID,
    trainer_id: uuid.UUID,
    disposition: str | None,
    team_slot: int | None,
    trainer_id_key: str | None,
    expired_at: dt.datetime | None,
) -> None:
    resolved_trainer_id = trainer_id if trainer_id_key == "trainer" else None
    await _insert_vibemon(
        sess,
        birth_snapshot_id=birth_snapshot_id,
        disposition=disposition,
        trainer_id=resolved_trainer_id,
        team_slot=team_slot,
        expired_at=expired_at,
    )


@pytest.mark.asyncio
async def test_disposition_constraint_rejects_owned_without_trainer(
    sess: AsyncSession,
    birth_snapshot_id: uuid.UUID,
) -> None:
    async def _commit_owned_without_trainer() -> None:
        await _insert_vibemon(
            sess,
            birth_snapshot_id=birth_snapshot_id,
            disposition="owned",
            trainer_id=None,
            team_slot=0,
        )
        await sess.commit()

    with pytest.raises(sa.exc.IntegrityError):
        await _commit_owned_without_trainer()
