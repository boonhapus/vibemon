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
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


async def test_adopt_candidate_claims_review_and_assigns_party_slot(
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

    row = (await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == candidate.id))).scalar_one()
    review = (
        await sess.execute(sa.select(models.CandidateReview).where(models.CandidateReview.vibemon_id == candidate.id))
    ).scalar_one()
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

    assert adopted.trainer_id == trainer_id
    assert adopted.team_slot == 0
    assert row.trainer_id == trainer_id
    assert row.team_slot == 0
    assert row.disposition == VibemonDispositionT.OWNED.value
    assert review.status == "adopted"
    assert review.resolution == "adopted"
    assert [event.event_type for event in history] == [
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.CANDIDATE_SHOWN.value,
        VibemonHistoryEventT.CANDIDATE_ADOPTED.value,
    ]
