from __future__ import annotations

from collections.abc import AsyncGenerator
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy as sa

from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.identity import Identity
from app.storage.database import models
from app.workflows.candidate import adopt_candidate, generate_candidate


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


class FakeProvider:
    name = "test-provider"

    async def fetch(self, seed: BirthSeed) -> dict[str, str]:
        return {"weather": "clear"}

    async def synthesize(self, seed: BirthSeed, payload: dict[str, str]) -> Affinity:
        return Affinity(
            identity=Identity(
                name="Testling",
                elements=(VibemonTypeT.FIRE,),
                base_hp=70,
                base_attack=75,
                base_defense=70,
                base_sp_attack=80,
                base_sp_defense=70,
                base_speed=90,
            ),
            intensity=1.0,
            provider_id=self.name,
            element_rankings={VibemonTypeT.FIRE: 1.0},
            moves=(
                Move(
                    id="test.ember",
                    name="Ember",
                    flavor_text="A tiny controlled flame.",
                    type=VibemonTypeT.FIRE,
                    category=MoveCategoryT.SPECIAL,
                    power=40,
                    accuracy=1.0,
                    pp=25,
                    target=MoveTargetT.SINGLE,
                ),
                Move(
                    id="test.flare",
                    name="Flare",
                    flavor_text="A quick flash of heat.",
                    type=VibemonTypeT.FIRE,
                    category=MoveCategoryT.SPECIAL,
                    power=50,
                    accuracy=0.95,
                    pp=20,
                    target=MoveTargetT.SINGLE,
                ),
            ),
        )


@pytest.mark.asyncio
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
        birth_seed=BirthSeed(timestamp=now, geo_coords=(41.8781, -87.6298), providers=[FakeProvider()]),
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
