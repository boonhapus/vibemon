"""Service orchestration for Vibemon generation, review, and ownership."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, cast
import datetime as dt
import random
import uuid

from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import sqlalchemy as sa

from app import lifecycle, models, schema, types
from app.data_store import assets as ds_assets
from app.data_store import monstore
from app.data_store import schema as ds_schema
from app.data_store import types as ds_types
from app.errors import (
    CandidateReviewUnavailable,
    GenerationAlreadyActive,
    GenerationCreditUnavailable,
    PartyFull,
    ReleaseUnavailable,
)
from app.plugins import move_catalog

DAILY_GENERATION_CREDITS = 3
CANDIDATE_REVIEW_TIMEOUT = dt.timedelta(hours=24)
GENERATION_HOLD_TIMEOUT = dt.timedelta(minutes=10)
REJECTION_ENCOUNTER_MULTIPLIER = 0.0
REJECTION_COOLDOWN_MIN = dt.timedelta(days=1)
REJECTION_COOLDOWN_MAX = dt.timedelta(days=3)

type Clock = Callable[[], dt.datetime]
type LifecycleStep = Callable[[schema.Vibemon], Awaitable[schema.Vibemon]]
type AssetUrler = Callable[[str, dt.timedelta], Awaitable[str]]


class _AdoptionPlan:
    def __init__(self, *, slot: int, release: models.Vibemon | None) -> None:
        self.slot = slot
        self.release = release


class VibemonService:
    """Application seam for Vibemon generation and trainer ownership workflows."""

    def __init__(
        self,
        *,
        clock: Clock | None = None,
        rng: random.Random | None = None,
        christen_step: LifecycleStep = lifecycle.christen,
        manifest_step: LifecycleStep = lifecycle.manifest,
        asset_urler: AssetUrler | None = None,
    ) -> None:
        self._clock = clock or (lambda: dt.datetime.now(tz=dt.UTC))
        self._rng = rng or random.Random()
        self._christen = christen_step
        self._manifest = manifest_step
        self._asset_urler = asset_urler or _monstore_url

    async def generate_candidate(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        birth_seed: schema.BirthSeed,
        nickname: str | None = None,
        core_identity: str | None = None,
        bypass_credits: bool = False,
    ) -> schema.PublicVibemon:
        now = self._now()
        credit_day: models.GenerationCreditDay | None = None
        hold_id: uuid.UUID | None = None
        if not bypass_credits:
            credit_day, hold_id = await self._reserve_credit(sess, trainer_id=trainer_id, now=now)
        try:
            snapshot = await birth_seed.fetch_snapshot()
            affinities = await snapshot.regenerate(birth_seed.providers, birth_seed)
            vibemon = schema.Vibemon.birth(
                *affinities,
                birth_seed=birth_seed,
                nickname=nickname,
                core_identity=core_identity,
            )
            vibemon = await self._christen(vibemon)
            row = await self._persist_new_vibemon(
                sess,
                vibemon=vibemon,
                birth_seed=birth_seed,
                snapshot=snapshot,
            )
            review = self._create_review(row.id, trainer_id, now)
            sess.add(review)
            self._history(
                sess,
                row.id,
                types.VibemonHistoryEventT.CANDIDATE_SHOWN,
                now,
                {"trainer_id": str(trainer_id)},
            )
            if credit_day is not None and hold_id is not None:
                await self._consume_credit(sess, credit_day, hold_id)
            await sess.flush()
            loaded = await self._load_vibemon(sess, row.id)
            return await self._read_model(loaded, reviewing_trainer_id=trainer_id)
        except Exception:
            if credit_day is not None and hold_id is not None:
                await self._release_credit(sess, credit_day, hold_id)
            await sess.flush()
            raise

    async def adopt_candidate(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        vibemon_id: uuid.UUID,
        release_vibemon_id: uuid.UUID | None = None,
    ) -> schema.PublicVibemon:
        now = self._now()
        review = await self._pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
        if self._deadline_passed(review, now):
            await self._timeout_review(sess, review, now)
            await sess.flush()
            raise CandidateReviewUnavailable("Candidate review has timed out.")

        plan = await self._adoption_plan(sess, trainer_id=trainer_id, release_vibemon_id=release_vibemon_id)
        vibemon = await self._schema_from_row(review.vibemon)
        if vibemon.lifecycle is not types.VibemonLifecycleT.MANIFESTED:
            vibemon = await self._manifest(vibemon)

        if plan.release is not None:
            self._release_to_wild(sess, plan.release, trainer_id, now)
        self._apply_schema_to_row(review.vibemon, vibemon)
        review.vibemon.trainer_id = trainer_id
        review.vibemon.team_slot = plan.slot
        review.vibemon.disposition = types.VibemonDispositionT.OWNED.value
        review.vibemon.wild_entered_at = None
        review.vibemon.last_encountered_at = None
        review.status = types.CandidateReviewStatusT.ADOPTED.value
        review.resolution = types.CandidateReviewStatusT.ADOPTED.value
        review.resolved_at = now
        await self._persist_assets(sess, vibemon)
        self._history(
            sess,
            review.vibemon_id,
            types.VibemonHistoryEventT.CANDIDATE_ADOPTED,
            now,
            {"trainer_id": str(trainer_id)},
        )
        await sess.flush()
        loaded = await self._load_vibemon(sess, vibemon_id)
        return await self._read_model(loaded, reviewing_trainer_id=trainer_id)

    async def reject_candidate(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        vibemon_id: uuid.UUID,
    ) -> schema.PublicVibemon:
        now = self._now()
        review = await self._pending_review(sess, trainer_id=trainer_id, vibemon_id=vibemon_id)
        await self._resolve_to_wild(
            sess,
            review,
            now,
            status=types.CandidateReviewStatusT.REJECTED,
            event=types.VibemonHistoryEventT.CANDIDATE_REJECTED,
        )
        await sess.flush()
        loaded = await self._load_vibemon(sess, vibemon_id)
        return await self._read_model(loaded, reviewing_trainer_id=trainer_id)

    async def release_vibemon(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        vibemon_id: uuid.UUID,
    ) -> schema.PublicVibemon:
        """Release an owned Vibemon back to wild. Preserves progression, moves, history, assets."""
        now = self._now()
        row = (
            await sess.execute(
                sa.select(models.Vibemon)
                .where(
                    models.Vibemon.id == vibemon_id,
                    models.Vibemon.trainer_id == trainer_id,
                    models.Vibemon.disposition == types.VibemonDispositionT.OWNED.value,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise ReleaseUnavailable("Vibemon is not owned by this trainer.")
        self._release_to_wild(sess, row, trainer_id, now)
        await sess.flush()
        loaded = await self._load_vibemon(sess, vibemon_id)
        return await self._read_model(loaded, reviewing_trainer_id=trainer_id)

    def _release_to_wild(
        self,
        sess: AsyncSession,
        row: models.Vibemon,
        trainer_id: types.TrainerIdT,
        now: dt.datetime,
    ) -> None:
        row.trainer_id = None
        row.team_slot = None
        row.disposition = types.VibemonDispositionT.WILD.value
        row.wild_entered_at = now
        row.last_encountered_at = now
        self._history(sess, row.id, types.VibemonHistoryEventT.RELEASED, now, {"trainer_id": str(trainer_id)})

    async def resolve_review_timeouts(self, sess: AsyncSession) -> int:
        now = self._now()
        reviews = (
            (
                await sess.execute(
                    sa.select(models.CandidateReview)
                    .options(selectinload(models.CandidateReview.vibemon))
                    .where(
                        models.CandidateReview.status == types.CandidateReviewStatusT.PENDING.value,
                        models.CandidateReview.timeout_at <= now,
                    )
                )
            )
            .scalars()
            .all()
        )
        for review in reviews:
            await self._timeout_review(sess, review, now)
        await sess.flush()
        return len(reviews)

    async def resolve_stale_holds(
        self,
        sess: AsyncSession,
        *,
        timeout: dt.timedelta = GENERATION_HOLD_TIMEOUT,
    ) -> int:
        """Clear generation holds that have exceeded the timeout."""
        now = self._now()
        threshold = now - timeout
        result = await sess.execute(
            sa.update(models.GenerationCreditDay)
            .where(
                models.GenerationCreditDay.active_hold_id.is_not(None),
                models.GenerationCreditDay.hold_started_at <= threshold,
            )
            .values(active_hold_id=None, hold_started_at=None)
        )
        return cast(CursorResult[Any], result).rowcount or 0

    async def _timeout_review(self, sess: AsyncSession, review: models.CandidateReview, now: dt.datetime) -> None:
        await self._resolve_to_wild(
            sess,
            review,
            now,
            status=types.CandidateReviewStatusT.TIMED_OUT,
            event=types.VibemonHistoryEventT.CANDIDATE_TIMED_OUT,
        )

    async def _resolve_to_wild(
        self,
        sess: AsyncSession,
        review: models.CandidateReview,
        now: dt.datetime,
        *,
        status: types.CandidateReviewStatusT,
        event: types.VibemonHistoryEventT,
    ) -> None:
        review.status = status.value
        review.resolution = status.value
        review.resolved_at = now
        review.vibemon.trainer_id = None
        review.vibemon.team_slot = None
        review.vibemon.disposition = types.VibemonDispositionT.WILD.value
        review.vibemon.wild_entered_at = now
        review.vibemon.last_encountered_at = now
        await self._upsert_encounter_adjustment(sess, review.trainer_id, review.vibemon_id, status.value, now)
        self._history(sess, review.vibemon_id, event, now, {"trainer_id": str(review.trainer_id)})

    async def _adoption_plan(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        release_vibemon_id: uuid.UUID | None,
    ) -> _AdoptionPlan:
        await self._lock_trainer(sess, trainer_id)
        rows = (
            (
                await sess.execute(
                    sa.select(models.Vibemon)
                    .where(
                        models.Vibemon.trainer_id == trainer_id,
                        models.Vibemon.disposition == types.VibemonDispositionT.OWNED.value,
                    )
                    .with_for_update()
                )
            )
            .scalars()
            .all()
        )
        used = {row.team_slot for row in rows if row.team_slot is not None}
        if len(rows) < 6:
            return _AdoptionPlan(slot=next(slot for slot in range(6) if slot not in used), release=None)
        if release_vibemon_id is None:
            raise PartyFull("Adoption requires releasing one party Vibemon.")
        release = next((row for row in rows if row.id == release_vibemon_id), None)
        if release is None or release.team_slot is None:
            raise PartyFull("Release Vibemon is not owned by this trainer.")
        return _AdoptionPlan(slot=release.team_slot, release=release)

    async def _reserve_credit(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        now: dt.datetime,
    ) -> tuple[models.GenerationCreditDay, uuid.UUID]:
        await self._lock_trainer(sess, trainer_id)
        row = await self._credit_day(sess, trainer_id=trainer_id, credit_date=now.date())
        if row.active_hold_id is not None:
            if row.hold_started_at is not None and row.hold_started_at <= now - GENERATION_HOLD_TIMEOUT:
                row.active_hold_id = None
                row.hold_started_at = None
            else:
                raise GenerationAlreadyActive("Trainer already has an active generation hold.")
        if row.credits_consumed >= DAILY_GENERATION_CREDITS:
            raise GenerationCreditUnavailable("Trainer has no generation credits remaining today.")
        hold_id = uuid.uuid7()
        row.active_hold_id = hold_id
        row.hold_started_at = now
        await sess.flush()
        return row, hold_id

    async def _consume_credit(
        self,
        sess: AsyncSession,
        row: models.GenerationCreditDay,
        hold_id: uuid.UUID,
    ) -> None:
        if row.active_hold_id != hold_id:
            raise GenerationAlreadyActive("Generation hold changed before credit consumption.")
        row.credits_consumed += 1
        row.active_hold_id = None
        row.hold_started_at = None
        await sess.flush()

    async def _release_credit(
        self,
        sess: AsyncSession,
        row: models.GenerationCreditDay,
        hold_id: uuid.UUID,
    ) -> None:
        if row.active_hold_id == hold_id:
            row.active_hold_id = None
            row.hold_started_at = None
        await sess.flush()

    async def _credit_day(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        credit_date: dt.date,
    ) -> models.GenerationCreditDay:
        row = (
            await sess.execute(
                sa.select(models.GenerationCreditDay)
                .where(
                    models.GenerationCreditDay.trainer_id == trainer_id,
                    models.GenerationCreditDay.credit_date == credit_date,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            row = models.GenerationCreditDay(trainer_id=trainer_id, credit_date=credit_date)
            sess.add(row)
            await sess.flush()
        return row

    async def _lock_trainer(self, sess: AsyncSession, trainer_id: types.TrainerIdT) -> None:
        await sess.execute(sa.select(models.Trainer.id).where(models.Trainer.id == trainer_id).with_for_update())

    async def _persist_new_vibemon(
        self,
        sess: AsyncSession,
        *,
        vibemon: schema.Vibemon,
        birth_seed: schema.BirthSeed,
        snapshot: schema.BirthSnapshot,
    ) -> models.Vibemon:
        seed = models.BirthSeed(
            timestamp=birth_seed.timestamp,
            geo_coords=list(birth_seed.geo_coords),
        )
        snapshot_row = models.BirthSnapshot(birth_seed=seed, provider_payloads=snapshot.provider_payloads)
        row = models.Vibemon(
            id=vibemon.id,
            nickname=vibemon.nickname,
            xp=vibemon.xp,
            level=vibemon.level,
            evo_stage=int(vibemon.evo_stage),
            lifecycle=vibemon.lifecycle.value,
            disposition=None,
            team_slot=None,
            trainer_id=None,
            birth_snapshot=snapshot_row,
            wild_entered_at=None,
            last_encountered_at=None,
            expired_at=None,
        )
        row.identity = self._identity_row(vibemon)
        sess.add(row)
        await sess.flush()
        await self._persist_moves(sess, row, vibemon.moves)
        await self._persist_assets(sess, vibemon)
        return row

    async def _persist_moves(
        self,
        sess: AsyncSession,
        row: models.Vibemon,
        moves: tuple[schema.Move, ...],
    ) -> None:
        cache = await move_catalog.load_move_cache(sess)
        for slot, move in enumerate(moves):
            move_row, created, _ = move_catalog.upsert_move(move, cache)
            if created:
                sess.add(move_row)
                await sess.flush()
            sess.add(
                models.VibemonMove(
                    vibemon_id=row.id,
                    move_id=move_row.id,
                    learned_at_level=row.level,
                    learned_at_ts=self._now(),
                    active_slot=slot,
                )
            )

    async def _persist_assets(self, sess: AsyncSession, vibemon: schema.Vibemon) -> None:
        if vibemon.aesthetic is None:
            return
        await ds_assets.upsert(sess, vibemon.id, vibemon.aesthetic.assets.values())

    def _identity_row(self, vibemon: schema.Vibemon) -> models.Identity:
        identity = vibemon.identity
        return models.Identity(
            name=identity.name,
            visual_notes=identity.visual_notes,
            provider_visual_notes=identity.provider_visual_notes,
            elements=[element.value for element in identity.elements],
            base_hp=identity.base_hp,
            base_attack=identity.base_attack,
            base_defense=identity.base_defense,
            base_sp_attack=identity.base_sp_attack,
            base_sp_defense=identity.base_sp_defense,
            base_speed=identity.base_speed,
            evo_seed=int(identity.evo_seed),
            is_radiant=identity.is_radiant,
            generation=identity.generation,
            generated_at=identity.generated_at,
        )

    def _apply_schema_to_row(self, row: models.Vibemon, vibemon: schema.Vibemon) -> None:
        row.nickname = vibemon.nickname
        row.xp = vibemon.xp
        row.level = vibemon.level
        row.evo_stage = int(vibemon.evo_stage)
        row.lifecycle = vibemon.lifecycle.value
        row.identity.name = vibemon.identity.name

    def _create_review(
        self,
        vibemon_id: uuid.UUID,
        trainer_id: types.TrainerIdT,
        now: dt.datetime,
    ) -> models.CandidateReview:
        return models.CandidateReview(
            vibemon_id=vibemon_id,
            trainer_id=trainer_id,
            status=types.CandidateReviewStatusT.PENDING.value,
            shown_at=now,
            timeout_at=now + CANDIDATE_REVIEW_TIMEOUT,
            resolved_at=None,
            resolution=None,
        )

    async def _pending_review(
        self,
        sess: AsyncSession,
        *,
        trainer_id: types.TrainerIdT,
        vibemon_id: uuid.UUID,
    ) -> models.CandidateReview:
        review = (
            await sess.execute(
                sa.select(models.CandidateReview)
                .options(
                    selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.identity),
                    selectinload(models.CandidateReview.vibemon)
                    .selectinload(models.Vibemon.moves)
                    .selectinload(models.VibemonMove.move),
                    selectinload(models.CandidateReview.vibemon).selectinload(models.Vibemon.assets),
                )
                .where(
                    models.CandidateReview.trainer_id == trainer_id,
                    models.CandidateReview.vibemon_id == vibemon_id,
                    models.CandidateReview.status == types.CandidateReviewStatusT.PENDING.value,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if review is None:
            raise CandidateReviewUnavailable("No pending candidate review exists for this trainer and Vibemon.")
        return review

    async def _load_vibemon(self, sess: AsyncSession, vibemon_id: uuid.UUID) -> models.Vibemon:
        return (
            await sess.execute(
                sa.select(models.Vibemon)
                .options(
                    selectinload(models.Vibemon.identity),
                    selectinload(models.Vibemon.moves).selectinload(models.VibemonMove.move),
                    selectinload(models.Vibemon.assets),
                    selectinload(models.Vibemon.candidate_reviews),
                )
                .where(models.Vibemon.id == vibemon_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()

    async def _schema_from_row(self, row: models.Vibemon) -> schema.Vibemon:
        identity = schema.Identity(
            name=row.identity.name,
            visual_notes=row.identity.visual_notes,
            provider_visual_notes=row.identity.provider_visual_notes,
            elements=tuple(types.VibemonTypeT(element) for element in row.identity.elements),
            base_hp=row.identity.base_hp,
            base_attack=row.identity.base_attack,
            base_defense=row.identity.base_defense,
            base_sp_attack=row.identity.base_sp_attack,
            base_sp_defense=row.identity.base_sp_defense,
            base_speed=row.identity.base_speed,
            evo_seed=types.EvolutionStageT(row.identity.evo_seed),
            is_radiant=row.identity.is_radiant,
            generation=row.identity.generation,
            generated_at=row.identity.generated_at,
        )
        vibemon = schema.Vibemon(
            id=row.id,
            nickname=row.nickname,
            identity=identity,
            moves=tuple(_move_schema(vibemon_move.move) for vibemon_move in sorted(row.moves, key=_move_slot)),
            level=row.level,
            xp=row.xp,
            evo_stage=types.EvolutionStageT(row.evo_stage),
            trainer_id=row.trainer_id,
            team_slot=row.team_slot,
            lifecycle=types.VibemonLifecycleT(row.lifecycle),
        )
        vibemon.aesthetic = schema.Aesthetic.from_vibemon(vibemon)
        vibemon.aesthetic.assets = {ds_types.AssetKind(asset.kind): _asset_ref(row.id, asset) for asset in row.assets}
        return vibemon

    async def _read_model(
        self,
        row: models.Vibemon,
        *,
        reviewing_trainer_id: types.TrainerIdT | None = None,
    ) -> schema.PublicVibemon:
        vibemon = await self._schema_from_row(row)
        assets = await self._public_assets(row.assets)
        review = _visible_review(row.candidate_reviews, reviewing_trainer_id)
        aesthetic = vibemon.aesthetic
        return schema.PublicVibemon(
            id=vibemon.id,
            nickname=vibemon.nickname,
            name=vibemon.name,
            identity=vibemon.identity,
            moves=vibemon.moves,
            level=vibemon.level,
            xp=vibemon.xp,
            evo_stage=vibemon.evo_stage,
            lifecycle=vibemon.lifecycle,
            disposition=types.VibemonDispositionT(row.disposition) if row.disposition else None,
            trainer_id=row.trainer_id,
            team_slot=row.team_slot,
            primary_color=aesthetic.primary_color if aesthetic else None,
            secondary_color=aesthetic.secondary_color if aesthetic else None,
            background_color=aesthetic.background_color if aesthetic else None,
            assets=assets,
            candidate_review=review,
        )

    async def _public_assets(self, assets: list[models.VibemonAsset]) -> tuple[schema.PublicAsset, ...]:
        public = []
        for asset in sorted(assets, key=lambda item: item.kind):
            public.append(
                schema.PublicAsset(
                    kind=ds_types.AssetKind(asset.kind),
                    url=await self._asset_urler(asset.object_key, dt.timedelta(hours=1)),
                    content_type=asset.content_type,
                    byte_size=asset.byte_size,
                    sha256=asset.sha256,
                )
            )
        return tuple(public)

    async def _upsert_encounter_adjustment(
        self,
        sess: AsyncSession,
        trainer_id: types.TrainerIdT,
        vibemon_id: uuid.UUID,
        source: str,
        now: dt.datetime,
    ) -> None:
        ends_at = now + self._cooldown_duration()
        adjustment = (
            await sess.execute(
                sa.select(models.EncounterAdjustment)
                .where(
                    models.EncounterAdjustment.trainer_id == trainer_id,
                    models.EncounterAdjustment.vibemon_id == vibemon_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if adjustment is None:
            adjustment = models.EncounterAdjustment(
                trainer_id=trainer_id,
                vibemon_id=vibemon_id,
                source=source,
                initial_multiplier=REJECTION_ENCOUNTER_MULTIPLIER,
                starts_at=now,
                ends_at=ends_at,
            )
            sess.add(adjustment)
            return
        adjustment.source = source
        adjustment.initial_multiplier = REJECTION_ENCOUNTER_MULTIPLIER
        adjustment.starts_at = now
        adjustment.ends_at = ends_at

    def _cooldown_duration(self) -> dt.timedelta:
        span = REJECTION_COOLDOWN_MAX - REJECTION_COOLDOWN_MIN
        return REJECTION_COOLDOWN_MIN + dt.timedelta(seconds=self._rng.random() * span.total_seconds())

    def _history(
        self,
        sess: AsyncSession,
        vibemon_id: uuid.UUID,
        event: types.VibemonHistoryEventT,
        occurred_at: dt.datetime,
        payload: dict[str, str],
    ) -> None:
        row = models.VibemonHistory(
            vibemon_id=vibemon_id,
            event_type=event.value,
            occurred_at=occurred_at,
            payload=payload,
        )
        sess.add(row)

    def _now(self) -> dt.datetime:
        now = self._clock()
        if now.tzinfo is None:
            return now.replace(tzinfo=dt.UTC)
        return now.astimezone(dt.UTC)

    def _deadline_passed(self, review: models.CandidateReview, now: dt.datetime) -> bool:
        timeout_at = review.timeout_at
        if timeout_at.tzinfo is None:
            timeout_at = timeout_at.replace(tzinfo=dt.UTC)
        return timeout_at <= now


def _move_schema(row: models.Move) -> schema.Move:
    return schema.Move(
        name=row.name,
        flavor_text=row.flavor_text,
        type=types.VibemonTypeT(row.type),
        category=types.MoveCategoryT(row.category),
        power=row.power,
        accuracy=row.accuracy,
        pp=row.pp,
        priority=row.priority,
        target=types.MoveTargetT(row.target),
        level_requirement=row.level_requirement,
        effects=tuple(schema.EffectGroup.model_validate(group) for group in row.effects),
        behavior=schema.MoveBehavior.model_validate(row.behavior),
    )


def _move_slot(row: models.VibemonMove) -> int:
    return row.active_slot if row.active_slot is not None else 99


def _asset_ref(vibemon_id: uuid.UUID, row: models.VibemonAsset) -> ds_schema.AssetRef:
    return ds_schema.AssetRef(
        vibemon_id=vibemon_id,
        kind=ds_types.AssetKind(row.kind),
        key=row.object_key,
        content_type=row.content_type,
        byte_size=row.byte_size,
        sha256=row.sha256,
    )


def _visible_review(
    reviews: list[models.CandidateReview],
    reviewing_trainer_id: types.TrainerIdT | None,
) -> schema.CandidateReviewRead | None:
    if reviewing_trainer_id is None:
        return None
    for review in reviews:
        if review.trainer_id == reviewing_trainer_id:
            return schema.CandidateReviewRead(
                id=review.id,
                trainer_id=review.trainer_id,
                status=types.CandidateReviewStatusT(review.status),
                shown_at=review.shown_at,
                timeout_at=review.timeout_at,
                resolved_at=review.resolved_at,
                resolution=types.CandidateReviewStatusT(review.resolution) if review.resolution else None,
            )
    return None


async def _monstore_url(key: str, expires_in: dt.timedelta) -> str:
    return await monstore.url(key, expires_in=expires_in)
