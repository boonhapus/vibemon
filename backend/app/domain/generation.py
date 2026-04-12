from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Optional

from attrs import evolve

from app.domain.context import GenerationContext, SourceData
from app.domain.models import GenerateRequestBody, VibemonPayload, VibemonStats
from app.domain.moves import generate_moves
from app.domain.names import generate_name
from app.domain.stats import compute_stats, make_seed
from app.domain.visual import generate_visual_dna


def parse_generation_timestamp(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    s = raw.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def provider_active(provider: object, ctx: GenerationContext) -> bool:
    source_id = getattr(provider, "source_id", "")
    if source_id == "weather":
        return True
    return bool(ctx.auth_tokens.get(source_id))


def build_stat_origins(merged: SourceData) -> dict[str, str]:
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


def build_payload(
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
    origins = build_stat_origins(merged)
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


def assemble_generation_pair(
    request: GenerateRequestBody,
    player_ctx: GenerationContext,
    merged: SourceData,
    succeeded_provider_ids: list[str],
    enemy_uid: str,
) -> tuple[VibemonPayload, VibemonPayload]:
    weather_live = bool(merged.raw.get("weather_live"))
    player_fallback = not weather_live

    source_label = "+".join(succeeded_provider_ids) if succeeded_provider_ids else "merged"

    player = build_payload(
        uid=request.user_id,
        merged=merged,
        ctx=player_ctx,
        source=source_label,
        fallback=player_fallback,
    )

    # Mirror match: identical stats/moves/visual/name; separate uid for sprites/battle identity.
    enemy = evolve(copy.deepcopy(player), uid=enemy_uid, source="mirror")
    return player, enemy
