

import random
import uuid
from datetime import datetime, timezone
from typing import Optional

import structlog
from attrs import define, field

from app.schema import (
    GenerationContext,
    GenerationResult,
    Move,
    SourceData,
    VibemonPayload,
    VibemonStats,
    VisualDNA,
)

log = structlog.get_logger(__name__)

MOVE_POOL: dict[str, list[Move]] = {
    "Fire": [
        Move("Ember Slash", "Fire", "physical", 40, 100),
        Move("Sear Strike", "Fire", "physical", 65, 95),
        Move("Blaze Crash", "Fire", "physical", 90, 85),
        Move("Scorch Pulse", "Fire", "special", 45, 100),
        Move("Combustion", "Fire", "special", 75, 90),
        Move("Inferno", "Fire", "special", 110, 75, True),
    ],
    "Water": [
        Move("Surge Slam", "Water", "physical", 40, 100),
        Move("Riptide Bash", "Water", "physical", 65, 95),
        Move("Torrent Rush", "Water", "physical", 90, 85),
        Move("Drench Pulse", "Water", "special", 45, 100),
        Move("Cascade", "Water", "special", 75, 90),
        Move("Deluge", "Water", "special", 110, 75, True),
    ],
    "Ice": [
        Move("Frost Strike", "Ice", "physical", 40, 100),
        Move("Crystal Bash", "Ice", "physical", 65, 90),
        Move("Shatter Crash", "Ice", "physical", 90, 85),
        Move("Chill Pulse", "Ice", "special", 45, 100),
        Move("Glaciate", "Ice", "special", 75, 90),
        Move("Blizzard", "Ice", "special", 110, 70, True),
    ],
    "Grass": [
        Move("Vine Lash", "Grass", "physical", 40, 100),
        Move("Bramble Slam", "Grass", "physical", 65, 90),
        Move("Root Crash", "Grass", "physical", 90, 85),
        Move("Spore Pulse", "Grass", "special", 45, 100),
        Move("Bloom Burst", "Grass", "special", 75, 90),
        Move("Overgrowth", "Grass", "special", 110, 75, True),
    ],
    "Electric": [
        Move("Spark Strike", "Electric", "physical", 40, 100),
        Move("Volt Slam", "Electric", "physical", 65, 95),
        Move("Thunder Crash", "Electric", "physical", 90, 80),
        Move("Shock Pulse", "Electric", "special", 45, 100),
        Move("Discharge", "Electric", "special", 75, 90),
        Move("Thunderstrike", "Electric", "special", 110, 75, True),
    ],
    "Normal": [
        Move("Strike", "Normal", "physical", 40, 100),
        Move("Bash", "Normal", "physical", 65, 100),
        Move("Pummel", "Normal", "physical", 90, 95, True),
        Move("Force Pulse", "Normal", "special", 45, 100),
        Move("Rush Surge", "Normal", "special", 65, 95),
        Move("Overwhelm", "Normal", "special", 100, 85),
    ],
    "Dark": [
        Move("Shadow Strike", "Dark", "physical", 40, 100),
        Move("Hex Slash", "Dark", "physical", 65, 95),
        Move("Dread Crash", "Dark", "physical", 90, 85),
        Move("Curse Pulse", "Dark", "special", 45, 100),
        Move("Nightfall", "Dark", "special", 75, 90),
        Move("Void", "Dark", "special", 110, 70, True),
    ],
    "Psychic": [
        Move("Phase Strike", "Psychic", "physical", 40, 100),
        Move("Echo Bash", "Psychic", "physical", 65, 90),
        Move("Warp Crash", "Psychic", "physical", 90, 85),
        Move("Mind Pulse", "Psychic", "special", 45, 100),
        Move("Distortion", "Psychic", "special", 75, 90),
        Move("Mindbreak", "Psychic", "special", 110, 75, True),
    ],
    "Ground": [
        Move("Quake Strike", "Ground", "physical", 40, 100),
        Move("Boulder Slam", "Ground", "physical", 65, 95),
        Move("Landslide", "Ground", "physical", 90, 85, True),
        Move("Tremor Pulse", "Ground", "special", 45, 100),
        Move("Dust Surge", "Ground", "special", 65, 90),
        Move("Tectonic", "Ground", "special", 100, 75),
    ],
}

ELEMENT_BASE_HUES = {
    "Fire": 20.0,
    "Water": 210.0,
    "Ice": 190.0,
    "Electric": 55.0,
    "Grass": 115.0,
    "Ground": 32.0,
    "Dark": 275.0,
    "Psychic": 315.0,
    "Normal": 35.0,
}

ELEMENT_EYE_SHAPES = {
    "Fire": "diamond",
    "Water": "circle",
    "Ice": "slit",
    "Electric": "compound",
    "Grass": "circle",
    "Ground": "slit",
    "Dark": "slit",
    "Psychic": "diamond",
    "Normal": "circle",
}

SYLLABLES: dict[str, list[str]] = {
    "Fire": ["pyr", "emb", "bla", "sol", "ign", "kar", "tor", "vul", "cin", "scor"],
    "Water": ["aqu", "tid", "rip", "del", "vas", "mer", "flu", "tur", "bri", "cor"],
    "Ice": ["gla", "fro", "cry", "chi", "sno", "bor", "gel", "arc", "hal", "nim"],
    "Electric": ["vol", "sho", "zap", "amp", "thr", "kin", "cra", "sul", "ion", "nex"],
    "Grass": ["vir", "blo", "spr", "flo", "lea", "mos", "tho", "cha", "fer", "gro"],
    "Ground": ["ter", "bou", "qua", "sed", "gra", "mol", "cla", "dus", "bru", "erd"],
    "Dark": ["nox", "sha", "voi", "hex", "dre", "cur", "obs", "phe", "sco", "nul"],
    "Psychic": ["psi", "pha", "tel", "mne", "eso", "var", "mis", "eid", "zer", "kal"],
    "Normal": ["nor", "com", "bas", "sim", "ord", "gen", "pri", "pla", "ven", "mid"],
}

_SEED_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
MIN_STAT, MAX_STAT = 30, 230


def _make_seed(uid: str, src: str) -> int:
    return int(uuid.uuid5(_SEED_NS, f"{uid}:{src}").hex, 16)


def _factor_to_stat(factor: float, rng: random.Random) -> int:
    base = MIN_STAT + factor * (MAX_STAT - MIN_STAT)
    variance = rng.uniform(-0.10, 0.10) * base
    return max(1, min(255, round(base + variance)))


def _resolve_element(votes: list[tuple[str, float]]) -> str:
    if not votes:
        return "Normal"
    totals: dict[str, float] = {}
    for el, w in votes:
        totals[el] = totals.get(el, 0) + w
    return max(totals.items(), key=lambda x: x[1])[0]


def _generate_name(element: str, seed: int) -> str:
    pool = SYLLABLES.get(element, SYLLABLES["Normal"])
    rng = random.Random(seed)
    for _ in range(16):
        n = rng.randint(2, 3)
        parts = [rng.choice(pool) for _ in range(n)]
        name = "".join(parts)
        if len(set(c.isalpha() for c in name.replace(name[:2], ""))) > 2:
            continue
        return name[:1].upper() + name[1:10]
    return "".join(rng.choice(pool) for _ in range(2))[:1].upper()


def _generate_moves(element: str, stats: VibemonStats, seed: int) -> list[Move]:
    rng = random.Random(seed)
    pool = MOVE_POOL.get(element, MOVE_POOL["Normal"])
    signatures = [m for m in pool if m.is_signature]
    sig = signatures[0] if signatures else pool[0]
    candidates = [m for m in pool if not m.is_signature]

    def w(m: Move) -> float:
        wt = 1.0
        if m.category == "physical":
            wt *= stats.attack / 128.0
        elif m.category == "special":
            wt *= stats.sp_attack / 128.0
        return max(wt, 0.1)

    phys = [m for m in candidates if m.category == "physical"]
    spec = [m for m in candidates if m.category == "special"]
    p1 = rng.choices(phys, weights=[w(m) for m in phys], k=1)[0]
    p2 = rng.choices(spec, weights=[w(m) for m in spec], k=1)[0]
    seen = {p1.name, p2.name}
    rem = [m for m in candidates if m.name not in seen]
    p3 = rng.choices(rem, weights=[w(m) for m in rem], k=1)[0]
    return [sig, p1, p2, p3]


def _generate_visual(element: str, stats: VibemonStats, seed: int) -> VisualDNA:
    rng = random.Random(seed)
    base_hue = ELEMENT_BASE_HUES.get(element, 35.0)
    hue = (base_hue + rng.uniform(-15, 15)) % 360.0
    sat = 0.50 + (stats.sp_attack / 255.0) * 0.40
    lum = 0.55
    h_sec = (hue + 30.0 + rng.uniform(-10, 10)) % 360.0
    h_acc = (hue + 180.0 + rng.uniform(-20, 20)) % 360.0
    return VisualDNA(
        n_points=max(8, min(12, 8 + int((stats.speed / 255.0) * 4))),
        spikiness=max(0.0, min(0.6, 0.1 + (stats.attack / 255.0) * 0.5)),
        limb_count=0 if stats.hp < 85 else 1 if stats.hp <= 170 else 2,
        limb_style="wing"
        if rng.random() < 0.5
        else "elongated"
        if stats.speed > stats.defense
        else "stubby",
        eye_count=1 if stats.sp_attack > 170 else 2,
        eye_size=max(0.04, min(0.12, 0.04 + (stats.sp_defense / 255.0) * 0.08)),
        eye_shape=ELEMENT_EYE_SHAPES.get(element, "circle"),
        mouth_style="none"
        if stats.attack < 85
        else "line"
        if stats.attack < 170
        else "open"
        if stats.attack < 220
        else "fanged",
        texture_pattern="none"
        if stats.defense < 85
        else "dots"
        if stats.defense < 140
        else "stripes"
        if stats.defense < 190
        else "scales"
        if stats.defense < 220
        else "cracks",
        color_primary=(hue, sat, lum),
        color_secondary=(h_sec, sat * 0.85, min(lum * 1.05, 1.0)),
        color_accent=(h_acc, min(sat * 1.2, 1.0), lum * 0.90),
        color_eye=(h_acc, 0.90, 0.70),
        outline_weight=max(0.5, min(3.5, 0.5 + (stats.defense / 255.0) * 3.0)),
        glow_intensity=max(0.0, min(1.0, stats.sp_attack / 255.0)),
        size_scale=max(0.8, min(1.3, 0.8 + (stats.hp / 255.0) * 0.5)),
        animation_speed=max(0.5, min(2.0, 0.5 + (stats.speed / 255.0) * 1.5)),
    )


def _compute_stats(ctx: GenerationContext, seed: int) -> VibemonStats:
    rng = random.Random(seed)
    ts = ctx.timestamp
    lat, lon = ctx.latitude, ctx.longitude
    hp_f = 0.3 + 0.4 * ((ts.hour % 24) / 24.0)
    atk_f = 0.3 + 0.4 * ((ts.weekday() + 1) / 7.0)
    def_f = 0.3 + 0.4 * (abs(lat) / 90.0)
    spa_f = 0.3 + 0.4 * ((ts.month % 12) / 12.0)
    spd_f = 0.3 + 0.4 * ((ts.hour % 12) / 12.0)
    spd_f = 0.3 + 0.4 * ((abs(lon) % 180) / 180.0) if abs(lon) > abs(lat) else spd_f
    spe_f = 0.3 + 0.4 * ((ts.second % 60) / 60.0)
    votes = [
        ("Fire", hp_f),
        ("Water", 1.0 - hp_f),
        ("Grass", atk_f),
        ("Electric", def_f),
        ("Ice", spa_f),
        ("Normal", spd_f),
    ]
    element = _resolve_element(votes)
    hp = _factor_to_stat(hp_f, rng)
    atk = _factor_to_stat(atk_f, rng)
    def_stat = _factor_to_stat(def_f, rng)
    spa = _factor_to_stat(spa_f, rng)
    spd = _factor_to_stat(spd_f, rng)
    spe = _factor_to_stat(spe_f, rng)
    return VibemonStats(hp, atk, def_stat, spa, spd, spe, element)


def build_payload(uid: str, ctx: GenerationContext, source: str) -> VibemonPayload:
    seed = _make_seed(uid, "vibemon")
    log.debug("building_vibemon", uid=uid, source=source, seed=seed)
    stats = _compute_stats(ctx, seed)
    log.debug("stats_computed", stats=stats)
    name = _generate_name(stats.element, seed + 1)
    log.debug("name_generated", name=name)
    moves = _generate_moves(stats.element, stats, seed + 2)
    log.debug("moves_generated", moves=[m.name for m in moves])
    visual = _generate_visual(stats.element, stats, seed + 3)
    log.debug("visual_generated", visual_fields=visual)
    origins = {
        "hp": "temporal_cycle",
        "attack": "weekday_intensity",
        "defense": "latitude_factor",
        "sp_attack": "seasonal_pattern",
        "sp_defense": "longitude_factor",
        "speed": "second_granularity",
    }
    return VibemonPayload(
        uid=uid,
        name=name,
        source=source,
        stats=stats,
        moves=moves,
        visual_dna=visual,
        flavour_text=f"Discovered at {ctx.latitude:.1f}, {ctx.longitude:.1f} on {ctx.timestamp.isoformat()}",
        stat_origins=origins,
    )


def generate_pair(ctx: GenerationContext) -> GenerationResult:
    log.info(
        "generating_pair",
        user_id=ctx.user_id,
        lat=ctx.latitude,
        lon=ctx.longitude,
        ts=ctx.timestamp.isoformat(),
    )
    player = build_payload(ctx.user_id, ctx, "datetime")
    enemy_uid = f"enemy_{ctx.timestamp.strftime('%Y%m%d%H')}_{round(ctx.latitude, 1)}_{round(ctx.longitude, 1)}"
    enemy = build_payload(enemy_uid, ctx, "mirror")
    enemy.source = "mirror"
    log.info("pair_generated", player=player.name, enemy=enemy.name)
    return GenerationResult(player=player, enemy=enemy)
