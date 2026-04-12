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

    player, enemy = assemble_generation_pair(
        request,
        ctx,
        merged,
        succeeded_ids,
        enemy_uid,
    )

    if request.render_assets == "raster":
        pair_uid = player.uid
        # Mirror pair: generate player first so paired-camera prompts stay ordered; same DNA lock on both.
        if enemy.source == "mirror":
            player.sprite_url = await ensure_sprite(
                player, BattleContext.PLAYER, pair_identity_uid=pair_uid
            )
            enemy.sprite_url = await ensure_sprite(
                enemy, BattleContext.ENEMY, pair_identity_uid=pair_uid
            )
        else:
            player_url, enemy_url = await asyncio.gather(
                ensure_sprite(player, BattleContext.PLAYER, pair_identity_uid=pair_uid),
                ensure_sprite(enemy, BattleContext.ENEMY, pair_identity_uid=pair_uid),
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
