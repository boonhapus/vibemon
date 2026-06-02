"""Integration tests for music-enabled birth workflow gates."""

import datetime as dt
import uuid

import pytest

from app.core.errors import MusicLinkRequired
from app.domains.generation.seed import BirthSeed
from app.providers.music.provider import MusicProvider
from app.storage.secrets.repository import DbTrainerSecrets
from scripts import _common
from tests.providers.fake_provider import FakeProvider


@pytest.mark.asyncio
async def test_fetch_snapshot_requires_lastfm_link(database_url: str) -> None:
    trainer_id = uuid.uuid7()
    async with _common.session_scope(database_url=database_url) as sess:
        await _common.ensure_trainer(sess, trainer_id)
        seed = BirthSeed(
            timestamp=dt.datetime(2026, 5, 19, tzinfo=dt.UTC),
            geo_coords=(41.8781, -87.6298),
            trainer_id=trainer_id,
            providers=[MusicProvider(), FakeProvider()],
        )
        with pytest.raises(MusicLinkRequired):
            await seed.fetch_snapshot(DbTrainerSecrets(sess))
