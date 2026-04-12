from __future__ import annotations

from app.domain.models import Move, VibemonPayload, VibemonStats, VisualDNA
from app.infra.sprites import (
    BattleContext,
    _generate_prompt,
    _together_seed,
    vibemon_to_monster_state,
)


def _minimal_payload(*, uid: str, source: str) -> VibemonPayload:
    stats = VibemonStats(
        hp=100,
        attack=80,
        defense=90,
        sp_attack=70,
        sp_defense=75,
        speed=85,
        element="Grass",
    )
    dna = VisualDNA(
        n_points=10,
        spikiness=0.2,
        limb_count=2,
        limb_style="stubby",
        eye_count=2,
        eye_size=0.08,
        eye_shape="circle",
        mouth_style="line",
        texture_pattern="dots",
        color_primary=(55.0, 0.7, 0.5),
        color_secondary=(120.0, 0.6, 0.45),
        color_accent=(300.0, 0.5, 0.55),
        color_eye=(200.0, 0.8, 0.4),
        outline_weight=1.5,
        glow_intensity=0.2,
        size_scale=1.0,
        animation_speed=1.0,
    )
    moves = [
        Move("Vine Lash", "Grass", "physical", 40, 100, False),
        Move("Tackle", "Normal", "physical", 40, 100, False),
        Move("Growl", "Normal", "status", 0, 100, False),
        Move("Leech Seed", "Grass", "status", 0, 90, False),
    ]
    return VibemonPayload(
        uid=uid,
        name="Testmon",
        source=source,
        stats=stats,
        moves=moves,
        visual_dna=dna,
        flavour_text="",
        stat_origins={k: "Baseline" for k in ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed")},
        fallback=False,
    )


def test_paired_camera_in_player_prompt_when_paired_battle() -> None:
    """Regression: player source is never 'mirror', but paired copy must still apply."""
    p = _minimal_payload(uid="user-1", source="weather")
    m = vibemon_to_monster_state(p, BattleContext.PLAYER)
    text = _generate_prompt(m, p, paired_battle=True)
    assert "BATTLE SET" in text
    assert "exactly ONE creature" in text
    assert "STYLE LOCK" in text
    assert "this image ONLY" in text
    assert "BACK SPRITE" in text


def test_together_seed_differs_by_camera_same_pair_uid() -> None:
    uid = "same-user"
    a = _together_seed(uid, BattleContext.PLAYER)
    b = _together_seed(uid, BattleContext.ENEMY)
    assert a != b
