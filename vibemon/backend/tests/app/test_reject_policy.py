"""Candidate reject crew policy lives in the workflow, not HTTP."""

import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CandidateReviewUnavailable
from app.domains.generation.seed import BirthSeed
from app.storage.database import models
from app.workflows.candidate import generate_candidate, reject_candidate
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.mark.asyncio
async def test_reject_blocked_until_first_adoption(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 6, 11, 12, 0, tzinfo=dt.UTC)
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now)
    sess.add(models.Trainer(id=trainer_id, username="first-timer"))
    await sess.flush()

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

    with pytest.raises(CandidateReviewUnavailable, match="Adopt your first Vibemon"):
        await reject_candidate(sess, trainer_id=trainer_id, vibemon_id=candidate.id)
