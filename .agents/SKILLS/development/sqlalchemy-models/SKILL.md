---
name: sqlalchemy-models
description: Guide for creating SQLAlchemy models in the Vibemon project using modern syntax.
---

# SQLAlchemy Models Skill

Guide for creating SQLAlchemy models in the Vibemon project using modern syntax.

## Core Principles

### 1. Primary Keys: UUID7
Use `uuid.uuid7()` as default for all primary keys (Python 3.14+):
```python
id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
```

### 2. Minimal `mapped_column()` Usage
Only use `mapped_column()` when necessary:
- Primary key definition
- JSON type columns
- Unique constraints
- Explicit nullable when type annotation isn't enough

**Avoid** adding `mapped_column()` just to specify `String(255)` — `Mapped[str]` is sufficient.

```python
# Good - minimal
name: Mapped[str]
elements: Mapped[list[str]] = mapped_column(JSON)
power: Mapped[int | None]

# Avoid - verbose
name: Mapped[str] = mapped_column(String(255))
```

### 3. Nullable Inference
Use `| None` in type annotation for nullable fields. Do NOT add `nullable=True` — it's redundant:
```python
# Good
visual_notes: Mapped[str | None]
power: Mapped[int | None]

# Avoid
visual_notes: Mapped[str | None] = mapped_column(nullable=True)
```

### 4. JSON Columns
Use `= mapped_column(JSON)` for complex types (lists, dicts):
```python
elements: Mapped[list[str]] = mapped_column(JSON)
effect: Mapped[dict | None] = mapped_column(JSON)
```

### 5. Foreign Key Constraints in `__table_args__`
Always define FK constraints in `__table_args__` with CASCADE delete:
```python
__table_args__ = (
    ForeignKeyConstraint(
        ["affinity_id"],
        ["affinities.id"],
        name="fk_vibemon_affinity",
        ondelete="CASCADE"
    ),
)
```

### 6. Junction Tables
Define many-to-many junction tables as `Table()` objects with `__table_args__`:
```python
affinity_moves = Table(
    "affinity_moves",
    Base.metadata,
    Column("affinity_id", primary_key=True),
    Column("move_id", primary_key=True),
    __table_args__=(
        ForeignKeyConstraint(["affinity_id"], ["affinities.id"], name="fk_affinity_moves_affinity", ondelete="CASCADE"),
        ForeignKeyConstraint(["move_id"], ["moves.id"], name="fk_affinity_moves_move", ondelete="CASCADE"),
    ),
)
```

### 7. Relationships
Define relationships with `back_populates` for bidirectional navigation:
```python
affinity: Mapped["Affinity"] = relationship(back_populates="identity", uselist=False)
moves: Mapped[list["Move"]] = relationship(secondary=affinity_moves, back_populates="affinities")
```

## Quick Template

```python
from sqlalchemy import JSON, Table, Column, ForeignKeyConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import uuid

class Base(DeclarativeBase):
    pass

class MyModel(Base):
    __tablename__ = "my_models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    name: Mapped[str]
    data: Mapped[dict | None] = mapped_column(JSON)
    ref_id: Mapped[uuid.UUID] = mapped_column(unique=True)

    __table_args__ = (
        ForeignKeyConstraint(["ref_id"], ["other_table.id"], name="fk_my_model_ref", ondelete="CASCADE"),
    )

    ref: Mapped["OtherModel"] = relationship(back_populates="my_models")
```
