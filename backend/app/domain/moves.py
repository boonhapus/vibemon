from __future__ import annotations

import random

from app.domain.models import Move, VibemonStats

_MOVE_POOL: dict[str, list[Move]] = {
    "Fire": [
        Move("Ember Slash", "Fire", "physical", 40, 100, False, None),
        Move("Sear Strike", "Fire", "physical", 65, 95, False, None),
        Move("Blaze Crash", "Fire", "physical", 90, 85, False, None),
        Move("Scorch Pulse", "Fire", "special", 45, 100, False, None),
        Move("Combustion", "Fire", "special", 75, 90, False, None),
        Move("Inferno", "Fire", "special", 110, 75, True, None),
        Move("Heat Veil", "Fire", "status", 0, 100, False, "own_sp_atk_plus_1"),
        Move("Cinder Shroud", "Fire", "status", 0, 100, False, "enemy_defense_minus_1"),
    ],
    "Water": [
        Move("Surge Slam", "Water", "physical", 40, 100, False, None),
        Move("Riptide Bash", "Water", "physical", 65, 95, False, None),
        Move("Torrent Rush", "Water", "physical", 90, 85, False, None),
        Move("Drench Pulse", "Water", "special", 45, 100, False, None),
        Move("Cascade", "Water", "special", 75, 90, False, None),
        Move("Deluge", "Water", "special", 110, 75, True, None),
        Move("Mist Veil", "Water", "status", 0, 100, False, "own_sp_def_plus_1"),
        Move("Soak", "Water", "status", 0, 100, False, "enemy_sp_atk_minus_1"),
    ],
    "Ice": [
        Move("Frost Strike", "Ice", "physical", 40, 100, False, None),
        Move("Crystal Bash", "Ice", "physical", 65, 90, False, None),
        Move("Shatter Crash", "Ice", "physical", 90, 85, False, None),
        Move("Chill Pulse", "Ice", "special", 45, 100, False, None),
        Move("Glaciate", "Ice", "special", 75, 90, False, None),
        Move("Blizzard", "Ice", "special", 110, 70, True, None),
        Move("Ice Veil", "Ice", "status", 0, 100, False, "own_defense_plus_1"),
        Move("Freeze Shroud", "Ice", "status", 0, 100, False, "enemy_speed_minus_1"),
    ],
    "Grass": [
        Move("Vine Lash", "Grass", "physical", 40, 100, False, None),
        Move("Bramble Slam", "Grass", "physical", 65, 90, False, None),
        Move("Root Crash", "Grass", "physical", 90, 85, False, None),
        Move("Spore Pulse", "Grass", "special", 45, 100, False, None),
        Move("Bloom Burst", "Grass", "special", 75, 90, False, None),
        Move("Overgrowth", "Grass", "special", 110, 75, True, None),
        Move("Seed Drain", "Grass", "status", 0, 100, False, "leech_seed"),
        Move("Tangle", "Grass", "status", 0, 100, False, "enemy_speed_minus_1"),
    ],
    "Ground": [
        Move("Quake Strike", "Ground", "physical", 40, 100, False, None),
        Move("Boulder Slam", "Ground", "physical", 65, 95, False, None),
        Move("Landslide", "Ground", "physical", 90, 85, True, None),
        Move("Tremor Pulse", "Ground", "special", 45, 100, False, None),
        Move("Dust Surge", "Ground", "special", 65, 90, False, None),
        Move("Tectonic", "Ground", "special", 100, 75, False, None),
        Move("Sand Veil", "Ground", "status", 0, 100, False, "own_defense_plus_1"),
        Move("Burrow", "Ground", "status", 0, 100, False, "burrow"),
    ],
    "Normal": [
        Move("Strike", "Normal", "physical", 40, 100, False, None),
        Move("Bash", "Normal", "physical", 65, 100, False, None),
        Move("Pummel", "Normal", "physical", 90, 95, True, None),
        Move("Force Pulse", "Normal", "special", 45, 100, False, None),
        Move("Rush Surge", "Normal", "special", 65, 95, False, None),
        Move("Overwhelm", "Normal", "special", 100, 85, False, None),
        Move("Fortify", "Normal", "status", 0, 100, False, "own_defense_plus_1"),
        Move("Lunge", "Normal", "status", 0, 100, False, "own_speed_plus_1"),
    ],
    "Dark": [
        Move("Shadow Strike", "Dark", "physical", 40, 100, False, None),
        Move("Hex Slash", "Dark", "physical", 65, 95, False, None),
        Move("Dread Crash", "Dark", "physical", 90, 85, False, None),
        Move("Curse Pulse", "Dark", "special", 45, 100, False, None),
        Move("Nightfall", "Dark", "special", 75, 90, False, None),
        Move("Void", "Dark", "special", 110, 70, True, None),
        Move("Drain", "Dark", "status", 0, 100, False, "drain"),
        Move("Phantom Shroud", "Dark", "status", 0, 100, False, "enemy_sp_atk_minus_1"),
    ],
    "Electric": [
        Move("Spark Strike", "Electric", "physical", 40, 100, False, None),
        Move("Volt Slam", "Electric", "physical", 65, 95, False, None),
        Move("Thunder Crash", "Electric", "physical", 90, 80, False, None),
        Move("Shock Pulse", "Electric", "special", 45, 100, False, None),
        Move("Discharge", "Electric", "special", 75, 90, False, None),
        Move("Thunderstrike", "Electric", "special", 110, 75, True, None),
        Move("Static Field", "Electric", "status", 0, 100, False, "enemy_speed_minus_1"),
        Move("Charge", "Electric", "status", 0, 100, False, "own_attack_plus_1"),
    ],
    "Psychic": [
        Move("Phase Strike", "Psychic", "physical", 40, 100, False, None),
        Move("Echo Bash", "Psychic", "physical", 65, 90, False, None),
        Move("Warp Crash", "Psychic", "physical", 90, 85, False, None),
        Move("Mind Pulse", "Psychic", "special", 45, 100, False, None),
        Move("Distortion", "Psychic", "special", 75, 90, False, None),
        Move("Mindbreak", "Psychic", "special", 110, 75, True, None),
        Move("Foresee", "Psychic", "status", 0, 100, False, "own_speed_plus_1"),
        Move("Unravel", "Psychic", "status", 0, 100, False, "enemy_defense_minus_1"),
    ],
}


def _pool_for_element(element: str) -> list[Move]:
    return _MOVE_POOL.get(element) or _MOVE_POOL["Normal"]


def generate_moves(stats: VibemonStats, seed: int) -> list[Move]:
    rng = random.Random(seed)
    pool = _pool_for_element(stats.element)
    signatures = [m for m in pool if m.is_signature]
    signature = signatures[0] if signatures else pool[0]
    candidates = [m for m in pool if not m.is_signature]

    def weight(m: Move) -> float:
        w = 1.0
        if m.category == "physical":
            w *= stats.attack / 128.0
        if m.category == "special":
            w *= stats.sp_attack / 128.0
        if m.category == "status":
            w *= stats.sp_defense / 128.0
        return max(w, 0.1)

    physicals = [m for m in candidates if m.category == "physical"]
    specials = [m for m in candidates if m.category == "special"]

    phys_pick = rng.choices(physicals, weights=[weight(m) for m in physicals], k=1)[0]
    spec_pick = rng.choices(specials, weights=[weight(m) for m in specials], k=1)[0]
    guaranteed = [phys_pick, spec_pick]
    seen = {m.name for m in guaranteed}

    remaining = [m for m in candidates if m.name not in seen]
    third = rng.choices(remaining, weights=[weight(m) for m in remaining], k=1)[0]

    return [signature, phys_pick, spec_pick, third]
