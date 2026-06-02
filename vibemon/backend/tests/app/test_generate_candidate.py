import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.history import VibemonHistoryEventT
from app.storage.database import models
from app.workflows.candidate import generate_candidate
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.mark.asyncio
async def test_generate_candidate_persists_review_and_consumes_credit(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    await sess.flush()

    result = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=BirthSeed(
            timestamp=now,
            geo_coords=(41.8781, -87.6298),
            trainer_id=TEST_TRAINER_ID,
            providers=[FakeProvider()],
        ),
        nickname="Sparky",
    )

    review = (
        await sess.execute(sa.select(models.CandidateReview).where(models.CandidateReview.vibemon_id == result.id))
    ).scalar_one()
    credit_day = (
        await sess.execute(
            sa.select(models.GenerationCreditDay).where(models.GenerationCreditDay.trainer_id == trainer_id)
        )
    ).scalar_one()
    history = (
        (
            await sess.execute(
                sa.select(models.VibemonHistory)
                .where(models.VibemonHistory.vibemon_id == result.id)
                .order_by(models.VibemonHistory.occurred_at, models.VibemonHistory.id)
            )
        )
        .scalars()
        .all()
    )

    assert result.nickname == "Sparky"
    assert result.candidate_review is not None
    assert result.candidate_review.trainer_id == trainer_id
    assert review.status == "pending"
    assert credit_day.credits_consumed == 1
    assert credit_day.active_hold_id is None
    assert [event.event_type for event in history] == [
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.CANDIDATE_SHOWN.value,
    ]
    assert {event.payload["move_content_id"] for event in history[:2]} == {"test.ember", "test.flare"}
    assert {event.payload["source"] for event in history[:2]} == {"birth"}
