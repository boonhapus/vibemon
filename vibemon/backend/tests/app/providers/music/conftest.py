import pathlib
import uuid

import pytest

from app.domains.trainer import types as trainer_types
from app.providers.music.provider import MusicProvider
from tests.settings_env import apply_test_settings


class FakeTrainerSecrets:
    def __init__(
        self,
        *,
        session_key: str | None = "session-key",
        username: str | None = "trainer-one",
    ) -> None:
        self._session_key = session_key
        self._username = username

    async def get(self, trainer_id: uuid.UUID, kind: str) -> str | None:
        del trainer_id
        if kind == trainer_types.LASTFM_SESSION_KEY:
            return self._session_key
        if kind == trainer_types.LASTFM_USERNAME:
            return self._username
        return None


@pytest.fixture(autouse=True)
def isolated_api_cache_db(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    database_url: str,
) -> None:
    apply_test_settings(
        monkeypatch,
        database_url=database_url,
        cache_url=f"sqlite:///{(tmp_path / 'api_cache.db').as_posix()}",
    )
    from app.settings import Settings

    Settings.load(refresh=True)


@pytest.fixture
def music_provider() -> MusicProvider:
    return MusicProvider()


@pytest.fixture
def trainer_secrets() -> FakeTrainerSecrets:
    return FakeTrainerSecrets()
