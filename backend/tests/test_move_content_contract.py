from typing import ClassVar

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("aiosqlite")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app import models, schema, types
from app.plugins import move_catalog
from app.plugins.provider import VibeProvider


def _move(
    move_id: str,
    name: str,
    *,
    type_: types.VibemonTypeT = types.VibemonTypeT.NORMAL,
) -> schema.Move:
    return schema.Move(
        id=move_id,
        name=name,
        flavor_text="A test move.",
        type=type_,
        category=types.MoveCategoryT.PHYSICAL,
        power=40,
    )


class StaticMoveProvider(VibeProvider):
    name = "static"
    exposed_elements: ClassVar = [(types.VibemonTypeT.NORMAL, "test")]

    def __init__(self, moves: tuple[schema.Move, ...]) -> None:
        self._moves = moves

    async def fetch(self, seed: schema.BirthSeed) -> dict[str, object]:
        return {}

    async def synthesize(self, seed: schema.BirthSeed, payload: dict[str, object]) -> schema.Affinity:
        raise NotImplementedError

    def moves(self) -> tuple[schema.Move, ...]:
        return self._moves

    async def teardown(self) -> None:
        return None


def test_move_requires_stable_provider_scoped_id_format() -> None:
    with pytest.raises(ValueError, match="Move id must use"):
        _move("Bad Id", "Bad Move")


def test_move_keeps_current_name_fields_and_derives_temporary_id() -> None:
    move = schema.Move(
        name="Spark Tap!",
        flavor_text="A test move.",
        type=types.VibemonTypeT.ELECTRIC,
        category=types.MoveCategoryT.SPECIAL,
        power=30,
    )

    assert move.id == "legacy.spark_tap"
    assert move.name == "Spark Tap!"
    assert move.flavor_text == "A test move."


def test_validate_move_catalog_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="Duplicate move id"):
        move_catalog.validate_move_catalog(
            (
                _move("climate.spark_tap", "Spark Tap"),
                _move("climate.spark_tap", "Spark Tap 2"),
            )
        )


def test_validate_move_catalog_rejects_canonical_name_collisions() -> None:
    with pytest.raises(ValueError, match="canonical key"):
        move_catalog.validate_move_catalog(
            (
                _move("climate.spark_tap", "Spark-Tap"),
                _move("climate.spark_tap_alt", "spark tap!"),
            )
        )


@pytest.mark.asyncio
async def test_sync_provider_moves_persists_stable_content_id() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as sess:
            created, updated = await move_catalog.sync_provider_moves(
                sess,
                [StaticMoveProvider((_move("climate.spark_tap", "Spark Tap"),))],
            )

            cache = await move_catalog.load_move_cache(sess)
            assert created == 4  # 1 provider + 3 universal
            assert updated == 0
            assert "climate.spark_tap" in cache
            row = cache["climate.spark_tap"]
            assert row.name == "Spark Tap"
    finally:
        await engine.dispose()
