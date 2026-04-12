from __future__ import annotations

import math
import random
import uuid
from collections import defaultdict
from typing import Iterable

from app.domain.context import SourceData
from app.domain.models import VibemonStats

MIN_STAT = 30
MAX_STAT = 230

_SEED_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def make_seed(user_id: str, source_id: str) -> int:
    return int(uuid.uuid5(_SEED_NAMESPACE, f"{user_id}:{source_id}").hex, 16)


def factor_to_stat(factor: float, rng: random.Random) -> int:
    base = MIN_STAT + factor * (MAX_STAT - MIN_STAT)
    variance = rng.uniform(-0.10, 0.10) * base
    return max(1, min(255, round(base + variance)))


def _resolve_elements(votes: list[tuple[str, float]]) -> tuple[str, str | None]:
    if not votes:
        return "Normal", None
    totals: dict[str, float] = defaultdict(float)
    for el, w in votes:
        totals[el] += w
    ranked = sorted(totals.items(), key=lambda x: -x[1])
    primary = ranked[0][0]
    secondary: str | None = None
    if len(ranked) > 1:
        runner_w = ranked[1][1]
        winner_w = ranked[0][1]
        if winner_w > 0 and runner_w >= 0.5 * winner_w:
            secondary = ranked[1][0]
    return primary, secondary


def merge_source_data(sources: Iterable[SourceData]) -> SourceData:
    sources = list(sources)
    if not sources:
        return SourceData()

    scalar_fields = [
        "hp_factor",
        "attack_factor",
        "defense_factor",
        "sp_attack_factor",
        "sp_defense_factor",
        "speed_factor",
        "hue_primary",
        "hue_secondary",
        "luminosity",
    ]
    merged = SourceData()
    for field in scalar_fields:
        values = [getattr(s, field) for s in sources if getattr(s, field) is not None]
        if values:
            setattr(merged, field, sum(values) / len(values))

    vote_totals: dict[str, float] = defaultdict(float)
    for s in sources:
        for element, weight in s.element_votes:
            vote_totals[element] += weight
    merged.element_votes = sorted(vote_totals.items(), key=lambda x: -x[1])

    texts = [s.flavour_text for s in sources if s.flavour_text]
    merged.flavour_text = " | ".join(texts) if texts else None

    raw_parts: dict[str, object] = {}
    for s in sources:
        if s.raw:
            raw_parts.update(s.raw)
    merged.raw = raw_parts
    return merged


def compute_stats(merged: SourceData, seed: int) -> VibemonStats:
    rng = random.Random(seed)

    def f(name: str) -> float:
        v = getattr(merged, name)
        return 0.5 if v is None else float(v)

    hp = factor_to_stat(f("hp_factor"), rng)
    attack = factor_to_stat(f("attack_factor"), rng)
    defense = factor_to_stat(f("defense_factor"), rng)
    sp_attack = factor_to_stat(f("sp_attack_factor"), rng)
    sp_defense = factor_to_stat(f("sp_defense_factor"), rng)
    speed = factor_to_stat(f("speed_factor"), rng)

    primary, secondary = _resolve_elements(merged.element_votes)
    return VibemonStats(
        hp=hp,
        attack=attack,
        defense=defense,
        sp_attack=sp_attack,
        sp_defense=sp_defense,
        speed=speed,
        element=primary,
        element_secondary=secondary,
    )


def scale_enemy_stats(player_stats: VibemonStats, enemy_stats: VibemonStats) -> VibemonStats:
    player_bst = (
        player_stats.hp
        + player_stats.attack
        + player_stats.defense
        + player_stats.sp_attack
        + player_stats.sp_defense
        + player_stats.speed
    )
    enemy_bst = (
        enemy_stats.hp
        + enemy_stats.attack
        + enemy_stats.defense
        + enemy_stats.sp_attack
        + enemy_stats.sp_defense
        + enemy_stats.speed
    )

    lower = player_bst * 0.85
    upper = player_bst * 1.15

    if lower <= enemy_bst <= upper:
        return enemy_stats

    target_bst = max(lower, min(upper, enemy_bst))
    scale = target_bst / enemy_bst if enemy_bst else 1.0

    def adj(v: int) -> int:
        return max(1, min(255, round(v * scale)))

    return VibemonStats(
        hp=adj(enemy_stats.hp),
        attack=adj(enemy_stats.attack),
        defense=adj(enemy_stats.defense),
        sp_attack=adj(enemy_stats.sp_attack),
        sp_defense=adj(enemy_stats.sp_defense),
        speed=adj(enemy_stats.speed),
        element=enemy_stats.element,
        element_secondary=enemy_stats.element_secondary,
    )
