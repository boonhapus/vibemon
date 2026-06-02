import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import models
from app.workflows.candidate import adopt_candidate, generate_candidate
from app.workflows.release_vibemon import release_vibemon
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.mark.asyncio
async def test_release_vibemon_returns_owned_member_to_wild_supply(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    await sess.flush()

    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now)
    candidate = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=BirthSeed(
            timestamp=now,
            geo_coords=(41.8781, -87.6298),
            trainer_id=TEST_TRAINER_ID,
            providers=[FakeProvider()],
        ),
    )
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now + dt.timedelta(minutes=5))
    adopted = await adopt_candidate(
        sess,
        trainer_id=trainer_id,
        vibemon_id=candidate.id,
    )

    monkeypatch.setattr("app.workflows.release_vibemon.resolve_clock", lambda: now + dt.timedelta(minutes=10))
    released = await release_vibemon(
        sess,
        trainer_id=trainer_id,
        vibemon_id=adopted.id,
    )

    row = (await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == candidate.id))).scalar_one()
    history = (
        (
            await sess.execute(
                sa.select(models.VibemonHistory)
                .where(models.VibemonHistory.vibemon_id == candidate.id)
                .order_by(models.VibemonHistory.occurred_at, models.VibemonHistory.id)
            )
        )
        .scalars()
        .all()
    )

    assert released.trainer_id is None
    assert released.team_slot is None
    assert released.disposition == VibemonDispositionT.WILD
    assert row.trainer_id is None
    assert row.team_slot is None
    assert row.disposition == VibemonDispositionT.WILD.value
    released_at = (now + dt.timedelta(minutes=10)).replace(tzinfo=None)
    assert row.wild_entered_at == released_at
    assert row.last_encountered_at == released_at
    assert [event.event_type for event in history] == [
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.CANDIDATE_SHOWN.value,
        VibemonHistoryEventT.CANDIDATE_ADOPTED.value,
        VibemonHistoryEventT.RELEASED.value,
    ]
