from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Optional

from app.engine.models import GenerateRequestBody, VibemonPayload, VibemonStats
from app.engine.moves import generate_moves
from app.engine.names import generate_name
from app.engine.sprites import BattleContext, ensure_sprite
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
    origins: dict[str, list[str]] = {
        "hp": [], "attack": [], "defense": [],
        "sp_attack": [], "sp_defense": [], "speed": [],
    }

    if r.get("weather_live") is True:
        label = "Weather"
        if r.get("relative_humidity_pct") is not None:
            origins["hp"].append(f"Humidity {float(r['relative_humidity_pct']):.0f}% ({label})")
        else:
            origins["hp"].append(f"Moisture signal ({label})")
        if r.get("uv_index") is not None and float(r["uv_index"]) > 6:
            origins["attack"].append(f"Clear skies / UV boost ({label})")
        else:
            origins["attack"].append(f"Sky conditions ({label})")
        if r.get("precipitation_mm") is not None and float(r["precipitation_mm"]) > 5:
            origins["defense"].append(f"Heavy precipitation shield ({label})")
        else:
            origins["defense"].append(f"Atmospheric stability ({label})")
        origins["sp_attack"].append(f"Weather pattern variety ({label})")
        origins["sp_defense"].append(f"Pressure patterns ({label})")
        if r.get("wind_kmh") is not None:
            origins["speed"].append(f"Wind {float(r['wind_kmh']):.0f} km/h ({label})")
        else:
            origins["speed"].append(f"Airflow ({label})")
    elif not r.get("spotify"):
        origins["hp"].append("Seasonal endurance (datetime fallback)")
        origins["attack"].append("Weekday intensity (datetime fallback)")
        origins["defense"].append("Stability baseline (datetime fallback)")
        origins["sp_attack"].append("Creative drift (datetime fallback)")
        origins["sp_defense"].append("Focus baseline (datetime fallback)")
        origins["speed"].append("Daily tempo curve (datetime fallback)")

    if r.get("spotify"):
        label = "Spotify"
        if r.get("track_count_7d") is not None:
            origins["hp"].append(f"{r['track_count_7d']} tracks in 7d ({label})")
        if r.get("avg_bpm") is not None:
            origins["speed"].append(f"BPM avg {r['avg_bpm']} ({label})")
        if r.get("genre_count") is not None:
            origins["sp_attack"].append(f"{r['genre_count']} genres ({label})")
        tags = r.get("enrichment_tags", [])
        aggressive = [t for t in tags if t in ("metal", "punk", "hardcore")]
        calm = [t for t in tags if t in ("classical", "ambient", "folk")]
        if aggressive:
            origins["attack"].append(f"Genre intensity: {', '.join(aggressive[:3])} ({label})")
        if calm:
            origins["sp_defense"].append(f"Genre depth: {', '.join(calm[:3])} ({label})")
        if r.get("avg_listening_hour") is not None:
            h = r["avg_listening_hour"]
            if h >= 22 or h < 4:
                origins["sp_defense"].append(f"Night listener avg {h:.0f}h ({label})")

    return {
        stat: " + ".join(parts) if parts else "Baseline"
        for stat, parts in origins.items()
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
    succeeded_ids: list[str] = []
    sources: list[SourceData] = []
    for p, o in zip(active, outcomes):
        if isinstance(o, SourceData):
            sources.append(o)
            succeeded_ids.append(p.source_id)
    merged = merge_source_data(sources)
    weather_live = bool(merged.raw.get("weather_live"))
    player_fallback = not weather_live

    source_label = "+".join(succeeded_ids) if succeeded_ids else "merged"

    player = _build_payload(
        uid=request.user_id,
        merged=merged,
        ctx=ctx,
        source=source_label,
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
