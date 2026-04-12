from __future__ import annotations

import asyncio
from typing import Any

from app.domain.context import GenerationContext, SourceData
from app.domain.generation import (
    assemble_generation_pair,
    parse_generation_timestamp,
    provider_active,
)
from app.domain.models import GenerateRequestBody
from app.domain.stats import merge_source_data
from app.infra.providers.protocol import VibemonProvider
from app.infra.providers.registry import PROVIDER_REGISTRY as _default_provider_registry
from app.infra.providers.weather import WeatherProvider
from app.infra.sprites import BattleContext, ensure_sprite
from app.serialization import to_jsonable

# Tests patch this list to inject fake providers.
PROVIDER_REGISTRY: list[type[VibemonProvider]] = list(_default_provider_registry)


async def generate(request: GenerateRequestBody) -> dict[str, Any]:
    ts = parse_generation_timestamp(request.timestamp)
    ctx = GenerationContext(
        user_id=request.user_id,
        timestamp=ts,
        latitude=request.latitude,
        longitude=request.longitude,
        auth_tokens=dict(request.auth_tokens),
    )

    active: list[VibemonProvider] = []
    for cls in PROVIDER_REGISTRY:
        p = cls()
        if provider_active(p, ctx):
            active.append(p)

    outcomes = await asyncio.gather(
        *[p.fetch(ctx) for p in active],
        return_exceptions=True,
    )
    succeeded_ids: list[str] = []
    sources: list[SourceData] = []
    for p, o in zip(active, outcomes):
        if isinstance(o, SourceData):
            sources.append(o)
            succeeded_ids.append(p.source_id)
    merged = merge_source_data(sources)

    enemy_uid = (
        f"enemy_{ctx.timestamp.strftime('%Y%m%d%H')}"
        f"_{round(ctx.latitude or 0.0, 1)}_{round(ctx.longitude or 0.0, 1)}"
    )
    enemy_ctx = GenerationContext(
        user_id=enemy_uid,
        timestamp=ctx.timestamp,
        latitude=ctx.latitude,
        longitude=ctx.longitude,
        auth_tokens={},
    )
    enemy_merged = await WeatherProvider().fetch(enemy_ctx)

    player, enemy = assemble_generation_pair(
        request,
        ctx,
        merged,
        succeeded_ids,
        enemy_uid,
        enemy_ctx,
        enemy_merged,
    )

    if request.render_assets == "raster":
        player_url, enemy_url = await asyncio.gather(
            ensure_sprite(player, BattleContext.PLAYER),
            ensure_sprite(enemy, BattleContext.ENEMY),
        )
        player.sprite_url = player_url
        enemy.sprite_url = enemy_url

    return {
        "player": to_jsonable(player),
        "enemy": to_jsonable(enemy),
    }


async def generate_from_dict(body: dict[str, Any]) -> dict[str, Any]:
    from app.serialization import structure_generate_request

    req = structure_generate_request(body)
    return await generate(req)
