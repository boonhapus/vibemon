"""Post-generate candidate facing persistence."""

import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.generation.seed import BirthSeed
from app.domains.sprite import types as sprite_types
from app.storage.database import candidate_review_repo, models, vibemon_repo
from app.workflows import candidate_finalize
from app.workflows.candidate import generate_candidate
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


@pytest.mark.asyncio
async def test_record_candidate_review_facing_persists_review_and_row(sess: AsyncSession) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 6, 11, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="hatcher"))
    await sess.flush()

    candidate = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=BirthSeed(
            timestamp=now,
            geo_coords=(41.8781, -87.6298),
            trainer_id=trainer_id,
            providers=[FakeProvider()],
        ),
        christen=False,
    )

    row = await vibemon_repo.load_vibemon(sess, candidate.id)
    row.reference_detected_facing = sprite_types.SpriteFacing.RIGHT.value
    await sess.flush()

    facing = await candidate_finalize.record_candidate_review_facing(
        sess,
        trainer_id=trainer_id,
        vibemon_id=candidate.id,
    )

    review = await candidate_review_repo.load_pending_candidate_review(sess, trainer_id=trainer_id)
    assert review is not None
    assert facing == "right"
    assert review.reference_facing == "right"
    assert row.reference_detected_facing == sprite_types.SpriteFacing.RIGHT.value
