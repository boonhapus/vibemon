from __future__ import annotations

from app.engine.models import Move, VisualDNA, VibemonPayload, VibemonStats
from app.providers.base import SourceData
from app.serialization import converter, to_jsonable


def test_source_data_defaults() -> None:
    s = SourceData()
    assert s.hp_factor is None
    assert s.element_votes == []


def test_vibemon_payload_roundtrip() -> None:
    stats = VibemonStats(100, 80, 70, 90, 85, 95, "Fire", "Dark")
    dna = VisualDNA(
        n_points=10,
        spikiness=0.3,
        limb_count=1,
        limb_style="stubby",
        eye_count=2,
        eye_size=0.08,
        eye_shape="circle",
        mouth_style="line",
        texture_pattern="dots",
        color_primary=(10.0, 0.8, 0.5),
        color_secondary=(30.0, 0.7, 0.55),
        color_accent=(200.0, 0.9, 0.4),
        color_eye=(200.0, 0.9, 0.7),
        outline_weight=1.5,
        glow_intensity=0.4,
        size_scale=1.0,
        animation_speed=1.0,
    )
    moves = [
        Move("Inferno", "Fire", "special", 110, 75, True, None),
        Move("Strike", "Fire", "physical", 40, 100, False, None),
        Move("Pulse", "Fire", "special", 45, 100, False, None),
        Move("Veil", "Fire", "status", 0, 100, False, "buff"),
    ]
    payload = VibemonPayload(
        uid="u1",
        name="Pyrox",
        source="merged",
        stats=stats,
        moves=moves,
        visual_dna=dna,
        flavour_text="Warm",
        stat_origins={"hp": "x"},
        fallback=False,
    )
    raw = to_jsonable(payload)
    assert raw["uid"] == "u1"
    assert raw["moves"][0]["is_signature"] is True
    back = converter.structure(raw, VibemonPayload)
    assert back.stats.element == "Fire"
    assert back.visual_dna.color_primary == (10.0, 0.8, 0.5)
