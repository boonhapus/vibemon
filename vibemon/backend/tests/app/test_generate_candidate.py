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
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.identity import Identity
from app.storage.database import models
from app.workflows.candidate import generate_candidate


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
        birth_seed=BirthSeed(timestamp=now, geo_coords=(41.8781, -87.6298), providers=[FakeProvider()]),
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
        (await sess.execute(sa.select(models.VibemonHistory).where(models.VibemonHistory.vibemon_id == result.id)))
        .scalars()
        .all()
    )

    assert result.nickname == "Sparky"
    assert result.candidate_review is not None
    assert result.candidate_review.trainer_id == trainer_id
    assert review.status == "pending"
    assert credit_day.credits_consumed == 1
    assert credit_day.active_hold_id is None
    assert [event.event_type for event in history] == [VibemonHistoryEventT.CANDIDATE_SHOWN.value]
