

import asyncio
from datetime import datetime, timezone

import pytest
import structlog
import logging

from app.schema import GenerateRequest, GenerationContext, VibemonPayload
from app.components.core import generate_pair, build_payload
from app.plugins.datetime_provider import DatetimeProvider

logging.basicConfig(level=logging.INFO)
structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO))

log = structlog.get_logger(__name__)


def parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    s = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@pytest.mark.asyncio
async def test_generate_pair_creates_player_and_enemy():
    req = GenerateRequest(
        user_id="player_1",
        latitude=51.5,
        longitude=-0.1,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    ts = parse_timestamp(req.timestamp)
    ctx = GenerationContext(
        user_id=req.user_id,
        timestamp=ts,
        latitude=req.latitude,
        longitude=req.longitude,
    )
    result = generate_pair(ctx)
    player, enemy = result.player, result.enemy
    log.info(
        "test_generate_pair_creates_player_and_enemy",
        player_uid=player.uid,
        player_name=player.name,
        player_element=player.stats.element,
        player_hp=player.stats.hp,
        player_moves=[m.name for m in player.moves],
        enemy_uid=enemy.uid,
        enemy_name=enemy.name,
    )
    assert player.uid == "player_1"
    assert player.stats.hp > 0
    assert len(player.moves) == 4
    assert all(m.power > 0 for m in player.moves if m.category != "status")
    assert enemy.uid.startswith("enemy_")
    assert enemy.source == "mirror"
    assert enemy.stats.hp > 0
    assert len(enemy.moves) == 4


@pytest.mark.asyncio
async def test_datetime_provider_provides_source_data():
    req = GenerateRequest(
        user_id="player_test",
        latitude=40.7128,
        longitude=-74.0060,
        timestamp="2026-04-17T12:00:00Z",
    )
    ts = parse_timestamp(req.timestamp)
    ctx = GenerationContext(
        user_id=req.user_id,
        timestamp=ts,
        latitude=req.latitude,
        longitude=req.longitude,
    )
    provider = DatetimeProvider()
    data = await provider.fetch(ctx)
    log.debug("datetime_provider_data", data=data)
    assert data.hp_factor is not None
    assert data.element_votes is not None
    assert len(data.element_votes) > 0


if __name__ == "__main__":
    asyncio.run(test_generate_pair_creates_player_and_enemy())
    asyncio.run(test_datetime_provider_provides_source_data())
    print("All tests passed!")
