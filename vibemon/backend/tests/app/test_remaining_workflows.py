import datetime as dt
import uuid

import pytest

pytest.importorskip("sqlalchemy")

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.adoption.types import CandidateReviewStatusT
from app.domains.encounter import tuning as encounter_tuning
from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.generation.seed import BirthSeed
from app.domains.trainer.credits import GENERATION_HOLD_TIMEOUT
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.disposition import VibemonDispositionT
from app.domains.vibemon.history import VibemonHistoryEventT
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.blob import assets as blob_assets
from app.storage.blob.monstore import MonStore
from app.storage.database import models
from app.workflows.candidate import generate_candidate, reject_candidate
from app.workflows.generate_wild_supply import generate_wild_supply
from app.workflows.prune_expired_assets import prune_expired_assets
from app.workflows.resolve_timeouts import resolve_review_timeouts, resolve_stale_holds
from app.workflows.wild_encounter import expire_wild, record_wild_encounter_outcome
from tests.conftest import TEST_TRAINER_ID
from tests.providers.fake_provider import WorkflowFakeProvider as FakeProvider


def _birth_seed(now: dt.datetime) -> BirthSeed:
    return BirthSeed(
        timestamp=now,
        geo_coords=(41.8781, -87.6298),
        trainer_id=TEST_TRAINER_ID,
        providers=[FakeProvider()],
    )


def _wild_vibemon(vibemon_id: uuid.UUID, *, now: dt.datetime) -> models.Vibemon:
    seed = models.BirthSeed(timestamp=now, geo_coords=[41.8781, -87.6298], trainer_id=TEST_TRAINER_ID)
    snapshot = models.BirthSnapshot(birth_seed=seed, provider_payloads={})
    row = models.Vibemon(
        id=vibemon_id,
        nickname=None,
        xp=0,
        level=5,
        evo_stage=0,
        lifecycle=VibemonLifecycleT.BORN.value,
        disposition=VibemonDispositionT.WILD.value,
        crew_slot=None,
        trainer_id=None,
        birth_snapshot=snapshot,
        wild_entered_at=now,
        last_encountered_at=now,
        expired_at=None,
    )
    row.identity = models.Identity(
        name="Wildling",
        visual_notes=None,
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
    test_trainer: object,
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
    test_trainer: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trainer_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    sess.add(models.Trainer(id=trainer_id, username="tester"))
    await sess.flush()
    monkeypatch.setattr("app.workflows.candidate.resolve_clock", lambda: now)
    candidate = await generate_candidate(sess, trainer_id=trainer_id, birth_seed=_birth_seed(now))

    # Reject policy requires at least one owned crew member.
    owned = _wild_vibemon(uuid.uuid7(), now=now)
    owned.disposition = VibemonDispositionT.OWNED.value
    owned.trainer_id = trainer_id
    owned.crew_slot = 0
    owned.wild_entered_at = None
    owned.last_encountered_at = None
    sess.add(owned)
    await sess.flush()

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
    test_trainer: object,
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
async def test_expire_wild_and_prune_expired_assets(
    sess: AsyncSession, test_trainer: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    vibemon_id = uuid.uuid7()
    now = dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC)
    stale_at = now - encounter_tuning.WILD_EXPIRATION_WINDOW - dt.timedelta(seconds=1)
    monstore = MonStore("memory://")
    reference_key = monstore.vibemon_asset_key(vibemon_id, AssetKind.REFERENCE, revision=1)
    await monstore.put_bytes(reference_key, b"reference")
    sess.add(_wild_vibemon(vibemon_id, now=stale_at))
    sess.add(
        models.VibemonAsset(
            vibemon_id=vibemon_id,
            kind=AssetKind.REFERENCE.value,
            selected_revision=1,
            max_revision=1,
            object_key=reference_key,
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

    tracking_monstore = MonStore("memory://")
    tracking_monstore.vibemon_asset_key = monstore.vibemon_asset_key  # type: ignore[method-assign]
    tracking_monstore.delete = fake_delete  # type: ignore[method-assign]
    monkeypatch.setattr(blob_assets, "get_default_monstore", lambda: tracking_monstore)
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
    assert deleted_keys == [reference_key]
    assert list(remaining_assets) == []


@pytest.mark.asyncio
async def test_resolve_timeouts_marks_reviews_and_clears_stale_holds(
    sess: AsyncSession,
    test_trainer: object,
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
