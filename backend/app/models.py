from sqlalchemy import JSON, Table, Column, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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

    identity: Mapped["Identity"] = relationship(back_populates="affinity")
    vibemon: Mapped["Vibemon"] = relationship(back_populates="affinity", uselist=False)
    moves: Mapped[list["Move"]] = relationship(secondary=affinity_moves, back_populates="affinities")


class BirthContext(Base):
    __tablename__ = "birth_context"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    timestamp: Mapped[int]
    geo_coords: Mapped[list[float]] = mapped_column(JSON)
    provider_names: Mapped[list[str]] = mapped_column(JSON)

    vibemon: Mapped["Vibemon"] = relationship(back_populates="birth_context", uselist=False)


class Vibemon(Base):
    __tablename__ = "vibemon"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    nickname: Mapped[str | None]
    affinity_id: Mapped[uuid.UUID] = mapped_column(unique=True)
    birth_context_id: Mapped[uuid.UUID | None]
    level: Mapped[int]

    __table_args__ = (
        ForeignKeyConstraint(["affinity_id"], ["affinity.id"], name="fk_vibemon_affinity", ondelete="CASCADE"),
        ForeignKeyConstraint(
            ["birth_context_id"], ["birth_context.id"], name="fk_vibemon_birth_context", ondelete="SET NULL"
        ),
    )

    affinity: Mapped["Affinity"] = relationship(back_populates="vibemon")
    birth_context: Mapped["BirthContext | None"] = relationship(back_populates="vibemon")
    birth_affinities: Mapped[list["Affinity"]] = relationship(secondary=vibemon_birth_affinities)
