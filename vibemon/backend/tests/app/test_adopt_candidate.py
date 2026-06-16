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


def _birth_seed(now: dt.datetime) -> BirthSeed:
    return BirthSeed(
        timestamp=now,
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[FakeProvider()],
    )


async def test_adopt_candidate_claims_review_and_assigns_crew_slot(
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
        birth_seed=_birth_seed(now),
    )

    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now + dt.timedelta(minutes=5))
    adopted = await adopt_candidate(
        sess,
        trainer_id=trainer_id,
        vibemon_id=candidate.id,
        nickname="Sparky",
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
    assert adopted.nickname == "Sparky"
    assert adopted.crew_slot == 0
    assert row.trainer_id == trainer_id
    assert row.crew_slot == 0
    assert row.disposition == VibemonDispositionT.OWNED.value
    assert review.status == "adopted"
    assert review.resolution == "adopted"
    assert [event.event_type for event in history] == [
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.MOVE_LEARNED.value,
        VibemonHistoryEventT.CANDIDATE_SHOWN.value,
        VibemonHistoryEventT.CANDIDATE_ADOPTED.value,
    ]


async def test_adopt_candidate_swaps_release_when_crew_full(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="full-crew"))
    await sess.flush()

    owned_ids: list[uuid.UUID] = []
    for index in range(6):
        monkeypatch.setattr(
            "app.workflows.candidate.resolve_clock",
            lambda index=index: now + dt.timedelta(minutes=index),
        )
        candidate = await generate_candidate(
            sess,
            trainer_id=trainer_id,
            birth_seed=_birth_seed(now + dt.timedelta(minutes=index)),
            bypass_credits=True,
        )
        adopted = await adopt_candidate(
            sess,
            trainer_id=trainer_id,
            vibemon_id=candidate.id,
            nickname=f"Keeper{index}",
        )
        owned_ids.append(adopted.id)

    released_id = owned_ids[2]
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now + dt.timedelta(hours=1))
    incoming = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=_birth_seed(now + dt.timedelta(hours=1)),
        bypass_credits=True,
    )

    swapped = await adopt_candidate(
        sess,
        trainer_id=trainer_id,
        vibemon_id=incoming.id,
        release_vibemon_id=released_id,
        nickname="Newcomer",
    )

    released_row = (
        await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == released_id))
    ).scalar_one()
    incoming_row = (
        await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == incoming.id))
    ).scalar_one()
    owned_count = (
        await sess.execute(
            sa.select(sa.func.count())
            .select_from(models.Vibemon)
            .where(
                models.Vibemon.trainer_id == trainer_id,
                models.Vibemon.disposition == VibemonDispositionT.OWNED.value,
            )
        )
    ).scalar_one()

    assert swapped.nickname == "Newcomer"
    assert swapped.crew_slot == 2
    assert incoming_row.crew_slot == 2
    assert incoming_row.disposition == VibemonDispositionT.OWNED.value
    assert released_row.trainer_id is None
    assert released_row.crew_slot is None
    assert released_row.disposition == VibemonDispositionT.WILD.value
    assert owned_count == 6
