from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from app.engine.models import GenerateRequestBody, VibemonPayload, VibemonStats
from app.engine.moves import generate_moves
from app.engine.names import generate_name
from app.engine.stats import compute_stats, make_seed, merge_source_data, scale_enemy_stats
from app.engine.visual import generate_visual_dna
from app.providers.registry import PROVIDER_REGISTRY
from app.providers.base import GenerationContext, SourceData, VibemonProvider
from app.providers.weather import WeatherProvider
from app.serialization import to_jsonable


def _parse_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    s = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _provider_active(p: VibemonProvider, ctx: GenerationContext) -> bool:
    if p.source_id == "weather":
        return True
    return bool(ctx.auth_tokens.get(p.source_id))


def _build_stat_origins(merged: SourceData) -> dict[str, str]:
    r = merged.raw
    label = "Weather"
    if r.get("weather_live") is True:
        hp = (
            f"Humidity {float(r['relative_humidity_pct']):.0f}% ({label})"
            if r.get("relative_humidity_pct") is not None
            else f"Moisture signal ({label})"
        )
        atk = (
            f"Clear skies / UV boost ({label})"
            if r.get("uv_index") is not None and float(r["uv_index"]) > 6
            else f"Sky conditions ({label})"
        )
        if r.get("precipitation_mm") is not None and float(r["precipitation_mm"]) > 5:
            defe = f"Heavy precipitation shield ({label})"
        else:
            defe = f"Atmospheric stability ({label})"
        spa = f"Weather pattern variety ({label})"
        spd = (
            f"Wind {float(r['wind_kmh']):.0f} km/h ({label})"
            if r.get("wind_kmh") is not None
            else f"Airflow ({label})"
        )
        spd_def = f"Pressure patterns ({label})"
    else:
        hp = "Seasonal endurance (datetime fallback)"
        atk = "Weekday intensity (datetime fallback)"
        defe = "Stability baseline (datetime fallback)"
        spa = "Creative drift (datetime fallback)"
        spd_def = "Focus baseline (datetime fallback)"
        spd = "Daily tempo curve (datetime fallback)"
    return {
        "hp": hp,
        "attack": atk,
        "defense": defe,
        "sp_attack": spa,
        "sp_defense": spd_def,
        "speed": spd,
    }


def _build_payload(
    *,
    uid: str,
    merged: SourceData,
    ctx: GenerationContext,
    source: str,
    fallback: bool,
    stats: Optional[VibemonStats] = None,
) -> VibemonPayload:
    seed = make_seed(uid, "vibemon")
    if stats is None:
        stats = compute_stats(merged, seed)
    visual = generate_visual_dna(merged, stats, seed)
    moves = generate_moves(stats, seed)
    name = generate_name(stats.element, seed)
    origins = _build_stat_origins(merged)
    return VibemonPayload(
        uid=uid,
        name=name,
        source=source,
        stats=stats,
        moves=moves,
        visual_dna=visual,
        flavour_text=merged.flavour_text or "",
        stat_origins=origins,
        fallback=fallback,
    )


async def generate(request: GenerateRequestBody) -> dict[str, Any]:
    ts = _parse_timestamp(request.timestamp)
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
        if _provider_active(p, ctx):
            active.append(p)

    outcomes = await asyncio.gather(
        *[p.fetch(ctx) for p in active],
        return_exceptions=True,
    )
    sources = [o for o in outcomes if isinstance(o, SourceData)]
    merged = merge_source_data(sources)
    weather_live = bool(merged.raw.get("weather_live"))
    player_fallback = not weather_live

    player = _build_payload(
        uid=request.user_id,
        merged=merged,
        ctx=ctx,
        source="merged",
        fallback=player_fallback,
    )

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
    enemy_seed = make_seed(enemy_uid, "vibemon")
    enemy_stats_raw = compute_stats(enemy_merged, enemy_seed)
    enemy_stats = scale_enemy_stats(player.stats, enemy_stats_raw)
    enemy_fallback = not bool(enemy_merged.raw.get("weather_live"))

    enemy = _build_payload(
        uid=enemy_uid,
        merged=enemy_merged,
        ctx=enemy_ctx,
        source="weather",
        fallback=enemy_fallback,
        stats=enemy_stats,
    )

    return {
        "player": to_jsonable(player),
        "enemy": to_jsonable(enemy),
    }


async def generate_from_dict(body: dict[str, Any]) -> dict[str, Any]:
    from app.serialization import structure_generate_request

    req = structure_generate_request(body)
    return await generate(req)
