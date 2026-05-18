"""SQLAlchemy ORM table declarations for persisted Vibemon data.

Use this module for database schema shape: mapped columns, relationships,
constraints, and persistence-only metadata. Keep generation, lifecycle
orchestration, and object-store writes outside ORM models.
"""

from typing import Any
import datetime as dt
import uuid

from sqlalchemy import (
    JSON,
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Trainer(Base):
    __tablename__ = "trainer"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    username: Mapped[str] = mapped_column(unique=True)

    vibemons: Mapped[list[Vibemon]] = relationship(back_populates="trainer")
    candidate_reviews: Mapped[list[CandidateReview]] = relationship(back_populates="trainer")
    generation_credit_days: Mapped[list[GenerationCreditDay]] = relationship(back_populates="trainer")


class BirthSeed(Base):
    __tablename__ = "birth_seed"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    timestamp: Mapped[dt.datetime]
    geo_coords: Mapped[list[float]] = mapped_column(JSON)

    birth_snapshots: Mapped[list[BirthSnapshot]] = relationship(
        back_populates="birth_seed",
        cascade="all, delete-orphan",
        single_parent=True,
    )


class BirthSnapshot(Base):
    __tablename__ = "birth_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    birth_seed_id: Mapped[uuid.UUID]
    provider_payloads: Mapped[dict[str, dict[str, Any]]] = mapped_column(JSON)

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
    evo_stage: Mapped[int]
    lifecycle: Mapped[str]
    disposition: Mapped[str | None]
    team_slot: Mapped[int | None]
    trainer_id: Mapped[uuid.UUID | None]
    birth_snapshot_id: Mapped[uuid.UUID]
    wild_entered_at: Mapped[dt.datetime | None]
    last_encountered_at: Mapped[dt.datetime | None]
    expired_at: Mapped[dt.datetime | None]

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
            "team_slot IS NULL OR (team_slot >= 0 AND team_slot <= 5)",
            name="ck_vibemon_team_slot",
        ),
        Index(
            "uq_vibemon_team_slot",
            "trainer_id",
            "team_slot",
            unique=True,
            sqlite_where=text("team_slot IS NOT NULL"),
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
    provider_visual_notes: Mapped[str | None]
    elements: Mapped[list[str]] = mapped_column(JSON)
    base_hp: Mapped[int]
    base_attack: Mapped[int]
    base_defense: Mapped[int]
    base_sp_attack: Mapped[int]
    base_sp_defense: Mapped[int]
    base_speed: Mapped[int]
    evo_seed: Mapped[int]
    is_radiant: Mapped[bool]
    generation: Mapped[int] = mapped_column(default=0)
    generated_at: Mapped[dt.datetime]

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
    effects: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    behavior: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    __table_args__ = (CheckConstraint("priority BETWEEN -7 AND 7", name="ck_move_priority"),)


class VibemonMove(Base):
    __tablename__ = "vibemon_move"

    vibemon_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    move_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    learned_at_level: Mapped[int]
    learned_at_ts: Mapped[dt.datetime]
    active_slot: Mapped[int | None]

    __table_args__ = (
        ForeignKeyConstraint(
            ["vibemon_id"],
            ["vibemon.id"],
            name="fk_vibemon_move_vibemon",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["move_id"],
            ["move.id"],
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
        ),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="moves")
    move: Mapped[Move] = relationship()


class VibemonHistory(Base):
    __tablename__ = "vibemon_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID]
    event_type: Mapped[str]
    occurred_at: Mapped[dt.datetime]
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

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
    object_key: Mapped[str] = mapped_column(unique=True)
    content_type: Mapped[str]
    byte_size: Mapped[int]
    sha256: Mapped[str]
    created_at: Mapped[dt.datetime]
    updated_at: Mapped[dt.datetime]

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


class CandidateReview(Base):
    __tablename__ = "candidate_review"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    trainer_id: Mapped[uuid.UUID]
    status: Mapped[str]
    shown_at: Mapped[dt.datetime]
    timeout_at: Mapped[dt.datetime]
    resolved_at: Mapped[dt.datetime | None]
    resolution: Mapped[str | None]

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
        Index("ix_candidate_review_trainer_status", "trainer_id", "status"),
    )

    vibemon: Mapped[Vibemon] = relationship(back_populates="candidate_reviews")
    trainer: Mapped[Trainer] = relationship(back_populates="candidate_reviews")


class GenerationCreditDay(Base):
    __tablename__ = "generation_credit_day"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    trainer_id: Mapped[uuid.UUID]
    credit_date: Mapped[dt.date]
    credits_consumed: Mapped[int] = mapped_column(default=0)
    active_hold_id: Mapped[uuid.UUID | None]
    hold_started_at: Mapped[dt.datetime | None]

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
    starts_at: Mapped[dt.datetime]
    ends_at: Mapped[dt.datetime]

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
