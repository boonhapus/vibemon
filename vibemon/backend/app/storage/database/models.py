"""SQLAlchemy ORM table declarations for persisted Vibemon data.

Use this module for database schema shape: mapped columns, relationships,
constraints, and persistence-only metadata. Keep generation, lifecycle
orchestration, and object-store writes outside ORM models.
"""

from typing import Any
import datetime as dt
import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domains.vibemon.identity import BaseStats
from app.storage.database import types as db_types


class Base(DeclarativeBase):
    pass


class Trainer(Base):
    __tablename__ = "trainer"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    username: Mapped[str] = mapped_column(unique=True)
    reference_detected_facing: Mapped[str | None]

    vibemons: Mapped[list[Vibemon]] = relationship(back_populates="trainer")
    candidate_reviews: Mapped[list[CandidateReview]] = relationship(back_populates="trainer")
    generation_credit_days: Mapped[list[GenerationCreditDay]] = relationship(back_populates="trainer")
    secrets: Mapped[list[TrainerSecret]] = relationship(back_populates="trainer")
    assets: Mapped[list[TrainerAsset]] = relationship(
        back_populates="trainer",
        cascade="all, delete-orphan",
    )


class TrainerSecret(Base):
    __tablename__ = "trainer_secret"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    trainer_id: Mapped[uuid.UUID]
    kind: Mapped[str]
    ciphertext: Mapped[bytes]

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_trainer_secret_trainer",
            ondelete="CASCADE",
        ),
        UniqueConstraint("trainer_id", "kind", name="uq_trainer_secret_trainer_kind"),
    )

    trainer: Mapped[Trainer] = relationship(back_populates="secrets")


class BirthSeed(Base):
    __tablename__ = "birth_seed"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    timestamp: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    geo_coords: Mapped[list[float]] = mapped_column(db_types.JSON_STORE)
    trainer_id: Mapped[uuid.UUID]

    birth_snapshots: Mapped[list[BirthSnapshot]] = relationship(
        back_populates="birth_seed",
        cascade="all, delete-orphan",
        single_parent=True,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_birth_seed_trainer",
            ondelete="RESTRICT",
        ),
    )


class BirthSnapshot(Base):
    __tablename__ = "birth_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    birth_seed_id: Mapped[uuid.UUID]
    provider_payloads: Mapped[dict[str, dict[str, Any]]] = mapped_column(db_types.JSON_STORE)

    __table_args__ = (
        ForeignKeyConstraint(
            ["birth_seed_id"],
            ["birth_seed.id"],
            name="fk_birth_snapshot_birth_seed",
            ondelete="CASCADE",
        ),
    )

    birth_seed: Mapped[BirthSeed] = relationship(back_populates="birth_snapshots")
    vibemons: Mapped[list[Vibemon]] = relationship(back_populates="birth_snapshot")


class Vibemon(Base):
    __tablename__ = "vibemon"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    nickname: Mapped[str | None]
    xp: Mapped[int] = mapped_column(default=0)
    level: Mapped[int]
    growth_rate: Mapped[str] = mapped_column(default="medium")
    evo_stage: Mapped[int]
    lifecycle: Mapped[str]
    disposition: Mapped[str | None]
    crew_slot: Mapped[int | None]
    trainer_id: Mapped[uuid.UUID | None]
    birth_snapshot_id: Mapped[uuid.UUID]
    wild_entered_at: Mapped[dt.datetime | None] = mapped_column(db_types.TIMESTAMPTZ)
    last_encountered_at: Mapped[dt.datetime | None] = mapped_column(db_types.TIMESTAMPTZ)
    expired_at: Mapped[dt.datetime | None] = mapped_column(db_types.TIMESTAMPTZ)
    reference_detected_facing: Mapped[str | None]

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_vibemon_trainer",
            ondelete="SET NULL",
        ),
        ForeignKeyConstraint(
            ["birth_snapshot_id"],
            ["birth_snapshot.id"],
            name="fk_vibemon_birth_snapshot",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "crew_slot IS NULL OR (crew_slot >= 0 AND crew_slot <= 5)",
            name="ck_vibemon_crew_slot",
        ),
        CheckConstraint(
            "("
            "disposition IS NULL AND trainer_id IS NULL AND crew_slot IS NULL"
            ") OR ("
            "disposition = 'owned' AND trainer_id IS NOT NULL AND crew_slot IS NOT NULL"
            ") OR ("
            "disposition = 'wild' AND trainer_id IS NULL AND crew_slot IS NULL"
            ") OR ("
            "disposition = 'expired' "
            "AND trainer_id IS NULL "
            "AND crew_slot IS NULL "
            "AND expired_at IS NOT NULL"
            ")",
            name="ck_vibemon_disposition_shape",
        ),
        Index(
            "uq_vibemon_crew_slot",
            "trainer_id",
            "crew_slot",
            unique=True,
            sqlite_where=text("crew_slot IS NOT NULL"),
            postgresql_where=text("crew_slot IS NOT NULL"),
        ),
    )

    identity: Mapped[Identity] = relationship(
        back_populates="vibemon",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    birth_snapshot: Mapped[BirthSnapshot] = relationship(back_populates="vibemons")
    trainer: Mapped[Trainer | None] = relationship(back_populates="vibemons")
    moves: Mapped[list[VibemonMove]] = relationship(
        back_populates="vibemon",
        cascade="all, delete-orphan",
    )
    history: Mapped[list[VibemonHistory]] = relationship(
        back_populates="vibemon",
        cascade="all, delete-orphan",
    )
    assets: Mapped[list[VibemonAsset]] = relationship(
        back_populates="vibemon",
        cascade="all, delete-orphan",
    )
    candidate_reviews: Mapped[list[CandidateReview]] = relationship(
        back_populates="vibemon",
        cascade="all, delete-orphan",
    )
    encounter_adjustments: Mapped[list[EncounterAdjustment]] = relationship(
        back_populates="vibemon",
        cascade="all, delete-orphan",
    )


class Identity(Base):
    __tablename__ = "identity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    name: Mapped[str]
    visual_notes: Mapped[str | None]
    elements: Mapped[list[str]] = mapped_column(db_types.JSON_STORE)
    base_hp: Mapped[int]
    base_attack: Mapped[int]
    base_defense: Mapped[int]
    base_sp_attack: Mapped[int]
    base_sp_defense: Mapped[int]
    base_speed: Mapped[int]
    evo_seed: Mapped[int]
    is_radiant: Mapped[bool]
    generation: Mapped[int] = mapped_column(default=0)
    generated_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)

    @property
    def base(self) -> BaseStats:
        return BaseStats(
            hp=self.base_hp,
            attack=self.base_attack,
            defense=self.base_defense,
            sp_attack=self.base_sp_attack,
            sp_defense=self.base_sp_defense,
            speed=self.base_speed,
        )

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_identity_vibemon",
            ondelete="CASCADE",
        ),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="identity")


class Move(Base):
    __tablename__ = "move"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    content_id: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(unique=True)
    flavor_text: Mapped[str]
    type: Mapped[str]
    category: Mapped[str]
    power: Mapped[int | None]
    accuracy: Mapped[float | None]
    pp: Mapped[int] = mapped_column(default=10)
    priority: Mapped[int] = mapped_column(default=0)
    target: Mapped[str]
    level_requirement: Mapped[int] = mapped_column(default=1)
    effects: Mapped[list[dict[str, Any]]] = mapped_column(db_types.JSON_STORE, default=list)
    behavior: Mapped[dict[str, Any]] = mapped_column(db_types.JSON_STORE, default=dict)

    __table_args__ = (CheckConstraint("priority BETWEEN -7 AND 7", name="ck_move_priority"),)


class VibemonMove(Base):
    __tablename__ = "vibemon_move"

    vibemon_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    move_content_id: Mapped[str] = mapped_column(primary_key=True)
    active_slot: Mapped[int | None]

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_vibemon_move_vibemon",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["move_content_id"],
            ["move.content_id"],
            name="fk_vibemon_move_move",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "active_slot IS NULL OR (active_slot >= 0 AND active_slot <= 3)",
            name="ck_vibemon_move_slot",
        ),
        Index(
            "uq_vibemon_move_active_slot",
            "vibemon_id",
            "active_slot",
            unique=True,
            sqlite_where=text("active_slot IS NOT NULL"),
            postgresql_where=text("active_slot IS NOT NULL"),
        ),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="moves")
    move: Mapped[Move] = relationship()


class VibemonHistory(Base):
    __tablename__ = "vibemon_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID]
    event_type: Mapped[str]
    occurred_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    payload: Mapped[dict[str, Any]] = mapped_column(db_types.JSON_STORE, default=dict)

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_vibemon_history_vibemon",
            ondelete="CASCADE",
        ),
        Index("ix_vibemon_history_vibemon_occurred", "vibemon_id", "occurred_at"),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="history")


class VibemonAsset(Base):
    __tablename__ = "vibemon_asset"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID]
    kind: Mapped[str]
    selected_revision: Mapped[int]
    max_revision: Mapped[int]
    object_key: Mapped[str] = mapped_column(unique=True)
    content_type: Mapped[str]
    byte_size: Mapped[int]
    sha256: Mapped[str]
    display_anchor: Mapped[dict[str, Any] | None] = mapped_column(db_types.JSON_STORE, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    updated_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_vibemon_asset_vibemon",
            ondelete="CASCADE",
        ),
        UniqueConstraint("vibemon_id", "kind", name="uq_vibemon_asset_slot"),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="assets")


class TrainerAsset(Base):
    __tablename__ = "trainer_asset"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    trainer_id: Mapped[uuid.UUID]
    kind: Mapped[str]
    selected_revision: Mapped[int]
    max_revision: Mapped[int]
    object_key: Mapped[str] = mapped_column(unique=True)
    content_type: Mapped[str]
    byte_size: Mapped[int]
    sha256: Mapped[str]
    created_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    updated_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_trainer_asset_trainer",
            ondelete="CASCADE",
        ),
        UniqueConstraint("trainer_id", "kind", name="uq_trainer_asset_slot"),
    )

    trainer: Mapped[Trainer] = relationship(back_populates="assets")


class CandidateReview(Base):
    __tablename__ = "candidate_review"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    trainer_id: Mapped[uuid.UUID]
    status: Mapped[str]
    shown_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    timeout_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(db_types.TIMESTAMPTZ)
    resolution: Mapped[str | None]
    reference_facing: Mapped[str | None]
    provider_notes: Mapped[list[dict[str, str]]] = mapped_column(db_types.JSON_STORE, default=list)

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_candidate_review_vibemon",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_candidate_review_trainer",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "("
            "status = 'pending' AND resolved_at IS NULL AND resolution IS NULL"
            ") OR ("
            "status != 'pending' AND resolved_at IS NOT NULL AND resolution = status"
            ")",
            name="ck_candidate_review_resolution_state",
        ),
        Index("ix_candidate_review_trainer_status", "trainer_id", "status"),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="candidate_reviews")
    trainer: Mapped[Trainer] = relationship(back_populates="candidate_reviews")


class GenerationCreditDay(Base):
    __tablename__ = "generation_credit_day"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    trainer_id: Mapped[uuid.UUID]
    credit_date: Mapped[dt.date] = mapped_column(db_types.DATE)
    credits_consumed: Mapped[int] = mapped_column(default=0)
    active_hold_id: Mapped[uuid.UUID | None]
    hold_started_at: Mapped[dt.datetime | None] = mapped_column(db_types.TIMESTAMPTZ)

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_generation_credit_day_trainer",
            ondelete="CASCADE",
        ),
        UniqueConstraint("trainer_id", "credit_date", name="uq_generation_credit_day"),
        CheckConstraint("credits_consumed >= 0 AND credits_consumed <= 3", name="ck_generation_credit_day_consumed"),
    )

    trainer: Mapped[Trainer] = relationship(back_populates="generation_credit_days")


class EncounterAdjustment(Base):
    __tablename__ = "encounter_adjustment"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    trainer_id: Mapped[uuid.UUID]
    vibemon_id: Mapped[uuid.UUID]
    source: Mapped[str]
    initial_multiplier: Mapped[float]
    starts_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)
    ends_at: Mapped[dt.datetime] = mapped_column(db_types.TIMESTAMPTZ)

    __table_args__ = (
        ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.id"],
            name="fk_encounter_adjustment_trainer",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_encounter_adjustment_vibemon",
            ondelete="CASCADE",
        ),
        UniqueConstraint("trainer_id", "vibemon_id", name="uq_encounter_adjustment_pair"),
    )

    trainer: Mapped[Trainer] = relationship()
    vibemon: Mapped[Vibemon] = relationship(back_populates="encounter_adjustments")
