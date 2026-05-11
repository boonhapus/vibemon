"""SQLAlchemy ORM table declarations for persisted Vibemon data.

Use this module for database schema shape: mapped columns, relationships,
constraints, and persistence-only metadata. Keep generation, lifecycle
orchestration, and object-store writes outside ORM models.
"""

from sqlalchemy import JSON, Table, Column, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import datetime as dt
import uuid


class Base(DeclarativeBase):
    pass


affinity_moves = Table(
    "affinity_moves",
    Base.metadata,
    Column("affinity_id", primary_key=True),
    Column("move_id", primary_key=True),
    ForeignKeyConstraint(["affinity_id"], ["affinity.id"], name="fk_affinity_moves_affinity", ondelete="CASCADE"),
    ForeignKeyConstraint(["move_id"], ["move.id"], name="fk_affinity_moves_move", ondelete="CASCADE"),
)


vibemon_birth_affinities = Table(
    "vibemon_birth_affinities",
    Base.metadata,
    Column("vibemon_id", primary_key=True),
    Column("affinity_id", primary_key=True),
    ForeignKeyConstraint(["vibemon_id"], ["vibemon.id"], name="fk_vibemon_birth_vibemon", ondelete="CASCADE"),
    ForeignKeyConstraint(["affinity_id"], ["affinity.id"], name="fk_vibemon_birth_affinity", ondelete="CASCADE"),
)


class Identity(Base):
    __tablename__ = "identity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str]
    visual_notes: Mapped[str | None]
    elements: Mapped[list[str]] = mapped_column(JSON)
    base_hp: Mapped[int]
    base_attack: Mapped[int]
    base_defense: Mapped[int]
    base_sp_attack: Mapped[int]
    base_sp_defense: Mapped[int]
    base_speed: Mapped[int]
    evo_seed: Mapped[int]
    evo_stage: Mapped[str]
    is_radiant: Mapped[bool]

    affinity: Mapped["Affinity"] = relationship(back_populates="identity", uselist=False)


class Move(Base):
    __tablename__ = "move"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str] = mapped_column(unique=True)
    flavor_text: Mapped[str]
    type: Mapped[str]
    category: Mapped[str]
    power: Mapped[int | None]
    accuracy: Mapped[float | None]
    pp: Mapped[int]
    priority: Mapped[int]
    effect: Mapped[dict | None] = mapped_column(JSON)
    effects: Mapped[list[dict] | None] = mapped_column(JSON)
    level_requirement: Mapped[int]

    affinities: Mapped[list["Affinity"]] = relationship(secondary=affinity_moves, back_populates="moves")


class Affinity(Base):
    __tablename__ = "affinity"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    identity_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    visual_notes: Mapped[str | None]
    intensity: Mapped[float]
    provider_id: Mapped[str]

    __table_args__ = (
        ForeignKeyConstraint(["identity_id"], ["identity.id"], name="fk_affinity_identity", ondelete="CASCADE"),
    )

    identity: Mapped["Identity"] = relationship(
        back_populates="affinity", uselist=False, single_parent=True,
        cascade="all, delete-orphan",
    )
    vibemon: Mapped["Vibemon"] = relationship(back_populates="affinity", uselist=False)
    moves: Mapped[list["Move"]] = relationship(secondary=affinity_moves, back_populates="affinities")


class BirthSeed(Base):
    __tablename__ = "birth_seed"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    timestamp: Mapped[dt.datetime]
    geo_coords: Mapped[list[float]] = mapped_column(JSON)
    provider_names: Mapped[list[str]] = mapped_column(JSON)

    birth_snapshots: Mapped[list["BirthSnapshot"]] = relationship(
        back_populates="birth_seed", cascade="all, delete-orphan", single_parent=True,
    )


class BirthSnapshot(Base):
    __tablename__ = "birth_snapshot"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    birth_seed_id: Mapped[uuid.UUID]
    provider_payloads: Mapped[dict[str, dict]] = mapped_column(JSON)

    __table_args__ = (
        ForeignKeyConstraint(
            ["birth_seed_id"], ["birth_seed.id"], name="fk_birth_snapshot_birth_seed", ondelete="CASCADE"
        ),
    )

    birth_seed: Mapped["BirthSeed"] = relationship(back_populates="birth_snapshots")
    vibemons: Mapped[list["Vibemon"]] = relationship(back_populates="birth_snapshot")


class Vibemon(Base):
    __tablename__ = "vibemon"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    nickname: Mapped[str | None]
    affinity_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    birth_snapshot_id: Mapped[uuid.UUID | None]
    level: Mapped[int]

    __table_args__ = (
        ForeignKeyConstraint(["affinity_id"], ["affinity.id"], name="fk_vibemon_affinity", ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["birth_snapshot_id"], ["birth_snapshot.id"], name="fk_vibemon_birth_snapshot", ondelete="SET NULL"
        ),
    )

    affinity: Mapped["Affinity"] = relationship(
        back_populates="vibemon", cascade="all, delete-orphan", single_parent=True,
    )
    birth_snapshot: Mapped["BirthSnapshot | None"] = relationship(
        back_populates="vibemons",
    )
    birth_affinities: Mapped[list["Affinity"]] = relationship(
        secondary=vibemon_birth_affinities, cascade="all, delete-orphan", single_parent=True,
    )
