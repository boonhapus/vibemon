"""Shared pytest fixtures for the Vibemon backend."""

from collections.abc import AsyncGenerator, Generator
import os
import pathlib
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import pytest

from tests.settings_env import apply_test_settings

TEST_TRAINER_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")
_FALLBACK_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def database_url() -> Generator[str]:
    explicit = os.getenv("VIBEMON_TEST_DATABASE_URL")
    if explicit:
        yield explicit
        return
    app_url = os.getenv("VIBEMON_STORAGE__DATABASE", "")
    if app_url.startswith("postgresql"):
        yield app_url
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        yield _FALLBACK_SQLITE_URL
        return

    try:
        with PostgresContainer("postgres:16-alpine") as postgres:
            sync_url = postgres.get_connection_url()
            yield sync_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    except Exception:
        yield _FALLBACK_SQLITE_URL


@pytest.fixture(autouse=True)
def vibemon_settings(monkeypatch: pytest.MonkeyPatch, database_url: str, tmp_path: pathlib.Path) -> None:
    apply_test_settings(monkeypatch, database_url=database_url, tmp_path=tmp_path)
    from app.settings import Settings

    Settings.load(refresh=True)


@pytest.fixture
async def test_trainer(sess: AsyncSession) -> object:
    from app.storage.database import models

    row = await sess.get(models.Trainer, TEST_TRAINER_ID)
    if row is None:
        row = models.Trainer(id=TEST_TRAINER_ID, username="test-trainer")
        sess.add(row)
        await sess.flush()
    return row


@pytest.fixture
async def sess(database_url: str) -> AsyncGenerator[AsyncSession]:
    pytest.importorskip("sqlalchemy")
    if database_url.startswith("sqlite"):
        pytest.importorskip("aiosqlite")
    else:
        pytest.importorskip("asyncpg")

    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.storage.database import engine as db_engine
    from app.storage.database import models

    engine = db_engine.create_async_database_engine(database_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.drop_all)
            await conn.run_sync(models.Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()
