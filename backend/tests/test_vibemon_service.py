from collections.abc import AsyncGenerator
from typing import ClassVar
import datetime as dt
import random
import uuid

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import sqlalchemy as sa

from app import errors, models, schema, types
from app.data_store import schema as ds_schema
from app.data_store import types as ds_types
from app.plugins.provider import VibeProvider
from app.services import vibemon_service

NOW = dt.datetime(2026, 5, 17, 12, 0, tzinfo=dt.UTC)


class FakeProvider(VibeProvider):
    name = "fake"
    exposed_elements: ClassVar = [(types.VibemonTypeT.FIRE, "test heat")]

    async def fetch(self, seed: schema.BirthSeed) -> dict[str, object]:
        return {"ok": True}

    async def synthesize(self, seed: schema.BirthSeed, payload: dict[str, object]) -> schema.Affinity:
        return schema.Affinity(
            identity=schema.Identity(
                name="emberling",
                elements=(types.VibemonTypeT.FIRE,),
                base_hp=70,
                base_attack=70,
                base_defense=70,
                base_sp_attack=70,
                base_sp_defense=70,
                base_speed=70,
            ),
            provider_id=self.name,
            intensity=1.0,
            moves=self.moves(),
        )

    def moves(self) -> tuple[schema.Move, ...]:
        return (
            self._move("Spark Tap", types.MoveCategoryT.PHYSICAL),
            self._move("Cinder Ping", types.MoveCategoryT.SPECIAL),
        )

    async def teardown(self) -> None:
        return None

    def _move(self, name: str, category: types.MoveCategoryT) -> schema.Move:
        slug = name.casefold().replace(" ", "_")
        return schema.Move(
            id=f"fake.{slug}",
            name=name,
            flavor_text="A small testing hit.",
            type=types.VibemonTypeT.FIRE,
            category=category,
            power=40,
        )


async def fake_christen(vibemon: schema.Vibemon) -> schema.Vibemon:
    vibemon.identity.name = "Testmon"
    if vibemon.aesthetic is None:
        vibemon.aesthetic = schema.Aesthetic.from_vibemon(vibemon)
    vibemon.aesthetic.assets[ds_types.AssetKind.REFERENCE] = ds_schema.AssetRef(
        vibemon_id=vibemon.id,
        kind=ds_types.AssetKind.REFERENCE,
        key=f"{vibemon.id}/reference",
        content_type="image/png",
        byte_size=1,
        sha256="ref",
    )
    vibemon.aesthetic.assets[ds_types.AssetKind.CRY_BATTLE] = ds_schema.AssetRef(
        vibemon_id=vibemon.id,
        kind=ds_types.AssetKind.CRY_BATTLE,
        key=f"{vibemon.id}/cry",
        content_type="audio/mpeg",
        byte_size=1,
        sha256="cry",
    )
    vibemon.lifecycle = types.VibemonLifecycleT.CHRISTENED
    return vibemon


async def fake_manifest(vibemon: schema.Vibemon) -> schema.Vibemon:
    if vibemon.aesthetic is None:
        vibemon.aesthetic = schema.Aesthetic.from_vibemon(vibemon)
    vibemon.aesthetic.assets[ds_types.AssetKind.SHEET] = ds_schema.AssetRef(
        vibemon_id=vibemon.id,
        kind=ds_types.AssetKind.SHEET,
        key=f"{vibemon.id}/sheet",
        content_type="image/png",
        byte_size=1,
        sha256="sheet",
    )
    vibemon.lifecycle = types.VibemonLifecycleT.MANIFESTED
    return vibemon


async def failing_manifest(vibemon: schema.Vibemon) -> schema.Vibemon:
    raise RuntimeError("manifest failed")


async def fake_asset_url(key: str, expires_in: dt.timedelta) -> str:
    return f"asset://{key}"


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


def _service(now: dt.datetime = NOW) -> vibemon_service.VibemonService:
    return vibemon_service.VibemonService(
        clock=lambda: now,
        rng=random.Random(1),
        christen_step=fake_christen,
        manifest_step=fake_manifest,
        asset_urler=fake_asset_url,
    )


def _seed() -> schema.BirthSeed:
    return schema.BirthSeed(timestamp=NOW, geo_coords=(41.0, -87.0), providers=[FakeProvider()])


async def _trainer(sess: AsyncSession) -> uuid.UUID:
    trainer_id = uuid.uuid7()
    sess.add(models.Trainer(id=trainer_id, username=f"trainer-{trainer_id}"))
    await sess.flush()
    return trainer_id


@pytest.mark.asyncio
async def test_generate_candidate_consumes_credit_and_opens_review(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)

    result = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    assert result.lifecycle == types.VibemonLifecycleT.CHRISTENED
    assert result.disposition is None
    assert result.candidate_review is not None
    assert result.candidate_review.status == types.CandidateReviewStatusT.PENDING
    assert len(result.assets) == 2

    credit = (await sess.execute(sa.select(models.GenerationCreditDay))).scalar_one()
    assert credit.credits_consumed == 1
    assert credit.active_hold_id is None


@pytest.mark.asyncio
async def test_get_vibemon_exposes_review_metadata_only_to_reviewer(sess: AsyncSession) -> None:
    reviewer = await _trainer(sess)
    stranger = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=reviewer, birth_seed=_seed())

    reviewer_view = await _service().get_vibemon(sess, vibemon_id=generated.id, viewer_trainer_id=reviewer)
    stranger_view = await _service().get_vibemon(sess, vibemon_id=generated.id, viewer_trainer_id=stranger)
    public_view = await _service().get_vibemon(sess, vibemon_id=generated.id)

    assert reviewer_view.candidate_review is not None
    assert reviewer_view.candidate_review.trainer_id == reviewer
    assert stranger_view.candidate_review is None
    assert public_view.candidate_review is None


@pytest.mark.asyncio
async def test_get_vibemon_includes_type_matchup_summary(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    read_model = await _service().get_vibemon(sess, vibemon_id=generated.id, viewer_trainer_id=trainer_id)

    assert read_model.type_matchup.coverage.move_types == (types.VibemonTypeT.FIRE,)
    assert set(read_model.type_matchup.defense.weak_to) == {
        types.VibemonTypeT.WATER,
        types.VibemonTypeT.GROUND,
        types.VibemonTypeT.ROCK,
    }
    assert set(read_model.type_matchup.defense.resists) == {
        types.VibemonTypeT.FIRE,
        types.VibemonTypeT.GRASS,
        types.VibemonTypeT.ICE,
        types.VibemonTypeT.BUG,
        types.VibemonTypeT.STEEL,
        types.VibemonTypeT.FAIRY,
    }
    assert read_model.type_matchup.defense.immune_to == ()
    assert set(read_model.type_matchup.coverage.strong_against) == {
        types.VibemonTypeT.GRASS,
        types.VibemonTypeT.ICE,
        types.VibemonTypeT.BUG,
    }
    assert set(read_model.type_matchup.coverage.ineffective_against) == {
        types.VibemonTypeT.FIRE,
        types.VibemonTypeT.WATER,
        types.VibemonTypeT.ROCK,
        types.VibemonTypeT.DRAGON,
    }


@pytest.mark.asyncio
async def test_generate_wild_supply_creates_christened_wild_without_review(sess: AsyncSession) -> None:
    result = await _service().generate_wild_supply(sess, birth_seed=_seed())

    assert result.lifecycle == types.VibemonLifecycleT.CHRISTENED
    assert result.disposition == types.VibemonDispositionT.WILD
    assert result.candidate_review is None
    assert result.trainer_id is None
    assert result.team_slot is None


@pytest.mark.asyncio
async def test_failed_generation_releases_hold_without_consuming_credit(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)

    async def failing_christen(vibemon: schema.Vibemon) -> schema.Vibemon:
        raise RuntimeError("generation failed")

    service = vibemon_service.VibemonService(clock=lambda: NOW, christen_step=failing_christen)

    with pytest.raises(RuntimeError, match="generation failed"):
        await service.generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    credit = (await sess.execute(sa.select(models.GenerationCreditDay))).scalar_one()
    assert credit.credits_consumed == 0
    assert credit.active_hold_id is None


@pytest.mark.asyncio
async def test_reject_candidate_resolves_to_wild_with_encounter_adjustment(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    result = await _service().reject_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    assert result.disposition == types.VibemonDispositionT.WILD
    assert result.candidate_review is not None
    assert result.candidate_review.status == types.CandidateReviewStatusT.REJECTED
    adjustment = (await sess.execute(sa.select(models.EncounterAdjustment))).scalar_one()
    assert adjustment.initial_multiplier == 0.0


@pytest.mark.asyncio
async def test_record_wild_encounter_outcome_sets_expected_multiplier(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    await _service().reject_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    await _service().record_wild_encounter_outcome(
        sess,
        trainer_id=trainer_id,
        vibemon_id=generated.id,
        outcome=types.WildEncounterOutcomeT.RUN,
    )
    adjustment = (await sess.execute(sa.select(models.EncounterAdjustment))).scalar_one()
    assert adjustment.source == types.WildEncounterOutcomeT.RUN.value
    assert adjustment.initial_multiplier == 0.3


@pytest.mark.asyncio
async def test_adopt_candidate_assigns_owned_slot_and_manifests(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    result = await _service().adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    assert result.disposition == types.VibemonDispositionT.OWNED
    assert result.trainer_id == trainer_id
    assert result.team_slot == 0
    assert result.lifecycle == types.VibemonLifecycleT.MANIFESTED


@pytest.mark.asyncio
async def test_release_owned_vibemon_returns_to_wild(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    await _service().adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    later = NOW + dt.timedelta(hours=2)
    result = await _service(later).release_vibemon(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    assert result.disposition == types.VibemonDispositionT.WILD
    assert result.trainer_id is None
    assert result.team_slot is None
    assert result.lifecycle == types.VibemonLifecycleT.MANIFESTED
    assert len(result.assets) == 3
    row = await sess.get(models.Vibemon, generated.id)
    assert row is not None
    assert row.wild_entered_at is not None
    assert row.wild_entered_at.replace(tzinfo=dt.UTC) == later
    events = (
        (await sess.execute(sa.select(models.VibemonHistory).where(models.VibemonHistory.vibemon_id == generated.id)))
        .scalars()
        .all()
    )
    assert any(e.event_type == types.VibemonHistoryEventT.RELEASED.value for e in events)


@pytest.mark.asyncio
async def test_release_rejects_non_owner(sess: AsyncSession) -> None:
    owner = await _trainer(sess)
    stranger = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=owner, birth_seed=_seed())
    await _service().adopt_candidate(sess, trainer_id=owner, vibemon_id=generated.id)

    with pytest.raises(errors.ReleaseUnavailable):
        await _service().release_vibemon(sess, trainer_id=stranger, vibemon_id=generated.id)


@pytest.mark.asyncio
async def test_bypass_credits_skips_daily_cap(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    service = _service()
    for _ in range(4):
        await service.generate_candidate(
            sess,
            trainer_id=trainer_id,
            birth_seed=_seed(),
            bypass_credits=True,
        )
    credit = (await sess.execute(sa.select(models.GenerationCreditDay))).scalar_one_or_none()
    assert credit is None


@pytest.mark.asyncio
async def test_one_active_generation_per_trainer(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    row = models.GenerationCreditDay(
        trainer_id=trainer_id,
        credit_date=NOW.date(),
        credits_consumed=0,
        active_hold_id=uuid.uuid7(),
        hold_started_at=NOW,
    )
    sess.add(row)
    await sess.flush()

    with pytest.raises(errors.GenerationAlreadyActive):
        await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())


@pytest.mark.asyncio
async def test_adopt_after_timeout_rejects_and_resolves_to_wild(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    later = NOW + dt.timedelta(hours=25)

    with pytest.raises(errors.CandidateReviewUnavailable):
        await _service(later).adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)

    review = (await sess.execute(sa.select(models.CandidateReview))).scalar_one()
    assert review.status == types.CandidateReviewStatusT.TIMED_OUT.value
    row = await sess.get(models.Vibemon, generated.id)
    assert row is not None
    assert row.disposition == types.VibemonDispositionT.WILD.value


@pytest.mark.asyncio
async def test_full_party_adoption_swaps_atomically(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    owned_ids: list[uuid.UUID] = []
    for day_offset in range(2):
        day = NOW + dt.timedelta(days=day_offset)
        for _ in range(3):
            generated = await _service(day).generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
            await _service(day).adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)
            owned_ids.append(generated.id)
            if len(owned_ids) == 6:
                break
        if len(owned_ids) == 6:
            break

    day3 = NOW + dt.timedelta(days=2)
    new_candidate = await _service(day3).generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())

    with pytest.raises(errors.PartyFull):
        await _service(day3).adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=new_candidate.id)

    released = owned_ids[2]
    released_row = await sess.get(models.Vibemon, released)
    assert released_row is not None
    freed_slot = released_row.team_slot

    result = await _service(day3).adopt_candidate(
        sess,
        trainer_id=trainer_id,
        vibemon_id=new_candidate.id,
        release_vibemon_id=released,
    )

    assert result.trainer_id == trainer_id
    assert result.team_slot == freed_slot
    released_after = await sess.get(models.Vibemon, released)
    assert released_after is not None
    assert released_after.disposition == types.VibemonDispositionT.WILD.value
    assert released_after.team_slot is None
    owned_count = (
        await sess.execute(
            sa.select(sa.func.count())
            .select_from(models.Vibemon)
            .where(
                models.Vibemon.trainer_id == trainer_id,
                models.Vibemon.disposition == types.VibemonDispositionT.OWNED.value,
            )
        )
    ).scalar_one()
    assert owned_count == 6


@pytest.mark.asyncio
async def test_full_party_adoption_does_not_release_when_manifest_fails(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    owned_ids: list[uuid.UUID] = []
    for day_offset in range(2):
        day = NOW + dt.timedelta(days=day_offset)
        for _ in range(3):
            generated = await _service(day).generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
            await _service(day).adopt_candidate(sess, trainer_id=trainer_id, vibemon_id=generated.id)
            owned_ids.append(generated.id)

    day3 = NOW + dt.timedelta(days=2)
    new_candidate = await _service(day3).generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    released = owned_ids[2]
    failing_service = vibemon_service.VibemonService(
        clock=lambda: day3,
        rng=random.Random(1),
        christen_step=fake_christen,
        manifest_step=failing_manifest,
        asset_urler=fake_asset_url,
    )

    with pytest.raises(RuntimeError, match="manifest failed"):
        await failing_service.adopt_candidate(
            sess,
            trainer_id=trainer_id,
            vibemon_id=new_candidate.id,
            release_vibemon_id=released,
        )

    released_after = await sess.get(models.Vibemon, released)
    candidate_after = await sess.get(models.Vibemon, new_candidate.id)
    assert released_after is not None
    assert candidate_after is not None
    assert released_after.disposition == types.VibemonDispositionT.OWNED.value
    assert released_after.trainer_id == trainer_id
    assert candidate_after.disposition is None
    assert candidate_after.trainer_id is None


@pytest.mark.asyncio
async def test_timeout_resolution_moves_candidate_to_wild(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    generated = await _service().generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    later = NOW + dt.timedelta(hours=25)

    count = await _service(later).resolve_review_timeouts(sess)

    assert count == 1
    review = (await sess.execute(sa.select(models.CandidateReview))).scalar_one()
    vibemon = await sess.get(models.Vibemon, generated.id)
    assert review.status == types.CandidateReviewStatusT.TIMED_OUT.value
    assert vibemon is not None
    assert vibemon.disposition == types.VibemonDispositionT.WILD.value

    read_model = await _service(later).get_vibemon(sess, vibemon_id=generated.id, viewer_trainer_id=trainer_id)
    assert read_model.candidate_review is not None
    assert read_model.candidate_review.status_label == "Timed out"
    assert read_model.candidate_review.resolved_label == "Timed out"
    assert read_model.candidate_review.resolved_at == later


@pytest.mark.asyncio
async def test_prepare_wild_encounter_reveal_manifests_lazy_wild(sess: AsyncSession) -> None:
    generated = await _service().generate_wild_supply(sess, birth_seed=_seed())
    assert generated.lifecycle == types.VibemonLifecycleT.CHRISTENED

    prepared = await _service().prepare_wild_encounter_reveal(sess, vibemon_id=generated.id)
    assert prepared.lifecycle == types.VibemonLifecycleT.MANIFESTED
    assert len(prepared.assets) == 3


@pytest.mark.asyncio
async def test_record_actual_wild_encounter_resets_expiration_clock(sess: AsyncSession) -> None:
    generated = await _service().generate_wild_supply(sess, birth_seed=_seed())
    later = NOW + dt.timedelta(days=31)
    result = await _service(later).expire_stale_wild(sess)
    assert result == 1

    row = await sess.get(models.Vibemon, generated.id)
    assert row is not None
    row.disposition = types.VibemonDispositionT.WILD.value
    row.expired_at = None
    row.last_encountered_at = NOW - dt.timedelta(days=29)
    await sess.flush()

    await _service().record_actual_wild_encounter(
        sess,
        vibemon_id=generated.id,
        event=types.VibemonHistoryEventT.WILD_ENCOUNTER_STARTED,
    )
    refreshed = await sess.get(models.Vibemon, generated.id)
    assert refreshed is not None
    assert refreshed.last_encountered_at is not None
    assert refreshed.disposition == types.VibemonDispositionT.WILD.value


@pytest.mark.asyncio
async def test_expire_stale_wild_marks_terminal_disposition(sess: AsyncSession) -> None:
    generated = await _service().generate_wild_supply(sess, birth_seed=_seed())
    later = NOW + dt.timedelta(days=31)

    expired = await _service(later).expire_stale_wild(sess)
    assert expired == 1
    row = await sess.get(models.Vibemon, generated.id)
    assert row is not None
    assert row.disposition == types.VibemonDispositionT.EXPIRED.value
    assert row.expired_at is not None


@pytest.mark.asyncio
async def test_expire_stale_wild_does_not_delete_assets(sess: AsyncSession) -> None:
    generated = await _service().generate_wild_supply(sess, birth_seed=_seed())
    later = NOW + dt.timedelta(days=31)
    await _service(later).expire_stale_wild(sess)

    assets = (
        (await sess.execute(sa.select(models.VibemonAsset).where(models.VibemonAsset.vibemon_id == generated.id)))
        .scalars()
        .all()
    )
    assert len(assets) == 2


@pytest.mark.asyncio
async def test_prune_expired_assets_runs_as_separate_retention_workflow(
    sess: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = await _service().generate_wild_supply(sess, birth_seed=_seed())
    later = NOW + dt.timedelta(days=31)
    await _service(later).expire_stale_wild(sess)

    deleted_ids: list[uuid.UUID] = []

    async def fake_delete_for_vibemon(_sess: AsyncSession, vibemon_id: uuid.UUID) -> int:
        deleted_ids.append(vibemon_id)
        return 2

    monkeypatch.setattr(vibemon_service.ds_assets, "delete_for_vibemon", fake_delete_for_vibemon)

    deleted = await _service(later).prune_expired_assets(sess)
    assert deleted == 2
    assert deleted_ids == [generated.id]


@pytest.mark.asyncio
async def test_public_asset_url_ttl_is_centralized(sess: AsyncSession) -> None:
    trainer_id = await _trainer(sess)
    observed: list[dt.timedelta] = []

    async def capture_asset_url(key: str, expires_in: dt.timedelta) -> str:
        observed.append(expires_in)
        return f"asset://{key}"

    service = vibemon_service.VibemonService(
        clock=lambda: NOW,
        rng=random.Random(1),
        christen_step=fake_christen,
        manifest_step=fake_manifest,
        asset_urler=capture_asset_url,
    )
    result = await service.generate_candidate(sess, trainer_id=trainer_id, birth_seed=_seed())
    assert len(result.assets) == 2
    assert observed
    assert set(observed) == {dt.timedelta(minutes=15)}
