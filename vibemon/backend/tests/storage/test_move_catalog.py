from sqlalchemy.ext.asyncio import AsyncSession
import pytest

pytest.importorskip("sqlalchemy")

from app.domains.move.entity import Move
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT
from app.storage.database import move_catalog


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
