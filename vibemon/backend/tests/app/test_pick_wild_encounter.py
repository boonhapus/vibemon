from __future__ import annotations

from collections.abc import AsyncGenerator
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import models
from app.workflows.wild_encounter import pick_wild_encounter


@pytest.fixture
async def sess() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            yield session
    finally:
        await engine.dispose()


def _wild_vibemon(vibemon_id: uuid.UUID, *, name: str, now: dt.datetime) -> models.Vibemon:
    seed = models.BirthSeed(timestamp=now, geo_coords=[41.8781, -87.6298])
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    row = models.Vibemon(
        id=vibemon_id,
        nickname=None,
        xp=0,
        level=5,
        evo_stage=0,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.WILD.value,
        team_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=now,
        last_encountered_at=None,
        expired_at=None,
    )
    row.identity = models.Identity(
        name=name,
        visual_notes=None,
        provider_visual_notes=None,
        elements=["fire"],
        base_hp=70,
        base_attack=75,
        base_defense=70,
        base_sp_attack=80,
        base_sp_defense=70,
        base_speed=90,
        evo_seed=0,
        is_radiant=False,
        generated_at=now,
    )
    return row


@pytest.mark.asyncio
async def test_pick_wild_encounter_ignores_pending_review_candidates(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    eligible_id = uuid.uuid7()
    blocked_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username="encounter-tester"))
    sess.add(_wild_vibemon(eligible_id, name="Eligible", now=now))
    sess.add(_wild_vibemon(blocked_id, name="Blocked", now=now + dt.timedelta(minutes=1)))
    sess.add(
        models.CandidateReview(
            vibemon_id=blocked_id,
            trainer_id=trainer_id,
            status=CandidateReviewStatusT.PENDING.value,
            shown_at=now,
            timeout_at=now + dt.timedelta(minutes=15),
            resolved_at=None,
            resolution=None,
        )
    )
    await sess.flush()

    monkeypatch.setattr("app.domains.encounter.wild_encounter.resolve_clock", lambda _clock=None: now)
    result = await pick_wild_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=41.8781,
        longitude=-87.6298,
        party_strength=100.0,
        desired_supply=1,
    )

    assert result is not None
    assert result.vibemon_id == eligible_id
