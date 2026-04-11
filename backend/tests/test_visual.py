from __future__ import annotations

from app.engine.models import VibemonStats
from app.engine.stats import make_seed
from app.engine.visual import ELEMENT_EYE_SHAPES, generate_visual_dna
from app.providers.base import SourceData


def test_visual_dna_ranges_extremes() -> None:
    merged = SourceData(hue_primary=100.0, luminosity=0.5)
    low = VibemonStats(1, 1, 1, 1, 1, 1, "Fire", None)
    dna = generate_visual_dna(merged, low, make_seed("a", "vibemon"))
    assert 8 <= dna.n_points <= 12
    assert 0.0 <= dna.spikiness <= 0.6
    assert dna.eye_shape == ELEMENT_EYE_SHAPES["Fire"]
    for c in (dna.color_primary, dna.color_secondary, dna.color_accent, dna.color_eye):
        assert 0 <= c[0] < 360 or c[0] == 0
        assert 0 <= c[1] <= 1
        assert 0 <= c[2] <= 1


def test_eye_shape_all_elements() -> None:
    merged = SourceData()
    for el in ELEMENT_EYE_SHAPES:
        stats = VibemonStats(80, 80, 80, 80, 80, 80, el, None)
        dna = generate_visual_dna(merged, stats, make_seed(el, "v"))
        assert dna.eye_shape == ELEMENT_EYE_SHAPES[el]
