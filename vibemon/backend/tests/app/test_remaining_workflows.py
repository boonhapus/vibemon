from __future__ import annotations

from collections.abc import AsyncGenerator
from types import SimpleNamespace
import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy as sa

from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.encounter import tuning as encounter_tuning
from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.domains.trainer.credits import GENERATION_HOLD_TIMEOUT
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.blob import assets as blob_assets
from app.storage.database import models
from app.workflows.candidate import generate_candidate, reject_candidate
from app.workflows.generate_wild_supply import generate_wild_supply
from app.workflows.prune_expired_assets import prune_expired_assets
from app.workflows.resolve_timeouts import resolve_review_timeouts, resolve_stale_holds
from app.workflows.wild_encounter import expire_wild, record_wild_encounter_outcome


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


def _birth_seed(now: dt.datetime) -> BirthSeed:
    return BirthSeed(timestamp=now, geo_coords=(41.8781, -87.6298), providers=[FakeProvider()])


def _wild_vibemon(vibemon_id: uuid.UUID, *, now: dt.datetime) -> models.Vibemon:
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
        last_encountered_at=now,
        expired_at=None,
    )
    row.identity = models.Identity(
        name="Wildling",
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
async def test_generate_wild_supply_persists_wild_row(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    monkeypatch.setattr("app.workflows.generate_wild_supply.resolve_clock", lambda: now)

    result = await generate_wild_supply(sess, birth_seed=_birth_seed(now))

    row = (await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == result.id))).scalar_one()
    assert result.disposition == VibemonDispositionT.WILD
    assert row.disposition == VibemonDispositionT.WILD.value
    assert row.wild_entered_at == now.replace(tzinfo=None)
    assert row.last_encountered_at == now.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_reject_candidate_resolves_review_to_wild(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    await sess.flush()
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now)
    candidate = await generate_candidate(sess, trainer_id=trainer_id, birth_seed=_birth_seed(now))

    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now + dt.timedelta(minutes=5))
    result = await reject_candidate(
        sess,
        trainer_id=trainer_id,
        vibemon_id=candidate.id,
    )

    review = (
        await sess.execute(sa.select(models.CandidateReview).where(models.CandidateReview.vibemon_id == candidate.id))
    ).scalar_one()
    history = (
        (await sess.execute(sa.select(models.VibemonHistory).where(models.VibemonHistory.vibemon_id == candidate.id)))
        .scalars()
        .all()
    )
    assert result.disposition == VibemonDispositionT.WILD
    assert review.status == CandidateReviewStatusT.REJECTED.value
    assert history[-1].event_type == VibemonHistoryEventT.CANDIDATE_REJECTED.value


@pytest.mark.asyncio
async def test_record_wild_encounter_outcome_updates_history_and_adjustment(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    sess.add(_wild_vibemon(vibemon_id, now=now))
    await sess.flush()

    monkeypatch.setattr("app.workflows.wild_encounter.resolve_clock", lambda: now + dt.timedelta(minutes=1))
    await record_wild_encounter_outcome(
        sess,
        trainer_id=trainer_id,
        vibemon_id=vibemon_id,
        outcome=WildEncounterOutcomeT.RUN,
    )

    adjustment = (
        await sess.execute(
            sa.select(models.EncounterAdjustment).where(models.EncounterAdjustment.vibemon_id == vibemon_id)
        )
    ).scalar_one()
    history = (
        (await sess.execute(sa.select(models.VibemonHistory).where(models.VibemonHistory.vibemon_id == vibemon_id)))
        .scalars()
        .all()
    )
    assert adjustment.trainer_id == trainer_id
    assert adjustment.source == WildEncounterOutcomeT.RUN.value
    assert history[-1].event_type == VibemonHistoryEventT.WILD_ENCOUNTER_COMPLETED.value


@pytest.mark.asyncio
async def test_expire_wild_and_prune_expired_assets(sess: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    stale_at = now - encounter_tuning.WILD_EXPIRATION_WINDOW - dt.timedelta(seconds=1)
    sess.add(_wild_vibemon(vibemon_id, now=stale_at))
    sess.add(
        models.VibemonAsset(
            vibemon_id=vibemon_id,
            kind=AssetKind.REFERENCE.value,
            object_key="vibemon/test/reference.png",
            content_type="image/png",
            byte_size=10,
            sha256="abc",
            created_at=stale_at,
            updated_at=stale_at,
        )
    )
    await sess.flush()
    deleted_keys: list[str] = []

    async def fake_delete(key: str) -> None:
        deleted_keys.append(key)

    fake_monstore = SimpleNamespace(delete=fake_delete)
    monkeypatch.setattr(blob_assets, "get_default_monstore", lambda: fake_monstore)
    monkeypatch.setattr("app.workflows.wild_encounter.resolve_clock", lambda: now)
    monkeypatch.setattr("app.workflows.prune_expired_assets.resolve_clock", lambda: now)

    expired = await expire_wild(sess)
    pruned = await prune_expired_assets(sess)

    row = (await sess.execute(sa.select(models.Vibemon).where(models.Vibemon.id == vibemon_id))).scalar_one()
    remaining_assets = (
        await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == vibemon_id))
    ).scalars()
    assert expired == 1
    assert pruned == 1
    assert row.disposition == VibemonDispositionT.EXPIRED.value
    assert deleted_keys == ["vibemon/test/reference.png"]
    assert list(remaining_assets) == []


@pytest.mark.asyncio
async def test_resolve_timeouts_marks_reviews_and_clears_stale_holds(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    candidate_now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    timeout_now = candidate_now + dt.timedelta(hours=25)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    sess.add(
        models.GenerationCreditDay(
            trainer_id=trainer_id,
            credit_date=candidate_now.date() - dt.timedelta(days=1),
            credits_consumed=1,
            active_hold_id=uuid.uuid7(),
            hold_started_at=timeout_now - GENERATION_HOLD_TIMEOUT - dt.timedelta(seconds=1),
        )
    )
    await sess.flush()
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: candidate_now)
    candidate = await generate_candidate(
        sess,
        trainer_id=trainer_id,
        birth_seed=_birth_seed(candidate_now),
    )

    monkeypatch.setattr("app.workflows.resolve_timeouts.resolve_clock", lambda: timeout_now)
    reviews = await resolve_review_timeouts(sess)
    holds = await resolve_stale_holds(sess)

    review = (
        await sess.execute(sa.select(models.CandidateReview).where(models.CandidateReview.vibemon_id == candidate.id))
    ).scalar_one()
    credit_days = (
        await sess.execute(
            sa.select(models.GenerationCreditDay)
            .where(models.GenerationCreditDay.trainer_id == trainer_id)
            .order_by(models.GenerationCreditDay.credit_date)
        )
    ).scalars()
    assert reviews == 1
    assert holds == 1
    assert review.status == CandidateReviewStatusT.TIMED_OUT.value
    assert [credit_day.active_hold_id for credit_day in credit_days] == [None, None]
