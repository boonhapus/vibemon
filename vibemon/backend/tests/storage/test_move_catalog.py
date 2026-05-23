from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.storage.database import models, move_catalog


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


def _move(move_id: str, name: str) -> Move:
    return Move(
        id=move_id,
        name=name,
        flavor_text="A focused test move.",
        type=VibemonTypeT.FIRE,
        category=MoveCategoryT.SPECIAL,
        power=40,
        accuracy=1.0,
        pp=20,
        target=MoveTargetT.SINGLE,
    )


@pytest.mark.asyncio
async def test_move_catalog_creates_and_reuses_content_identity(sess: AsyncSession) -> None:
    cache = await move_catalog.load_move_cache(sess)
    row, created, changed = move_catalog.upsert_move(_move("test.spark", "Spark"), cache)
    sess.add(row)
    await sess.flush()

    cache = await move_catalog.load_move_cache(sess)
    reused, recreated, rechanging = move_catalog.upsert_move(_move("test.spark", "Spark"), cache)

    assert created is True
    assert changed is True
    assert recreated is False
    assert rechanging is False
    assert reused.id == row.id


@pytest.mark.asyncio
async def test_move_catalog_rejects_canonical_name_collision(sess: AsyncSession) -> None:
    cache = await move_catalog.load_move_cache(sess)
    row, _, _ = move_catalog.upsert_move(_move("test.fire_pulse", "Fire Pulse"), cache)
    sess.add(row)
    await sess.flush()

    cache = await move_catalog.load_move_cache(sess)
    with pytest.raises(ValueError, match="Move name collides"):
        move_catalog.upsert_move(_move("other.fire_pulse", "fire-pulse"), cache)
