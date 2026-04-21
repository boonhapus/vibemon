import attrs
import pytest

from app import birth
from app.plugins.protocol import ColorShift, Context, Delta, SourceData, VisualDelta
from app.sprite import Anatomy, ColorZone, Creature


@attrs.define
class FakeProvider:
    _name: str
    _intensity: float
    _delta: Delta

    @property
    def name(self) -> str:
        return self._name

    @property
    def affinities(self) -> set[str]:
        return set()

    async def intensity(self, context: Context) -> float:
        return self._intensity

    async def contribute(self, context: Context) -> Delta:
        return self._delta


def test_merge_plugin_influences_weighted_stats_and_visual():
    deltas = [
        (
            1.0,
            Delta(
                delta_stats={"attack": 100},
                delta_visual=VisualDelta(
                    color_shifts={"primary": ColorShift(hue_rotation=10.0, lightness_adjust=0.10)}
                ),
                delta_description="first",
            ),
        ),
        (
            0.25,
            Delta(
                delta_stats={"attack": 80},
                delta_visual=VisualDelta(
                    color_shifts={
                        "primary": ColorShift(
                            hue_rotation=-8.0,
                            lightness_adjust=0.04,
                            hex_override="#111111",
                        )
                    }
                ),
                delta_description="second",
            ),
        ),
    ]

    stats, visual, fragments, glow_candidates = birth._merge_plugin_influences(deltas)

    assert stats["attack"] == 120
    assert visual.color_shifts["primary"].hue_rotation == pytest.approx(8.0)
    assert visual.color_shifts["primary"].lightness_adjust == pytest.approx(0.11)
    assert visual.color_shifts["primary"].hex_override == "#111111"
    assert fragments == ["first", "second"]
    assert glow_candidates == []


def test_merge_plugin_influences_weighted_hex_winner():
    deltas = [
        (
            0.2,
            Delta(
                delta_visual=VisualDelta(
                    color_shifts={"trim": ColorShift(hex_override="#AAAAAA")}
                )
            ),
        ),
        (
            0.9,
            Delta(
                delta_visual=VisualDelta(
                    color_shifts={"trim": ColorShift(hex_override="#BBBBBB")}
                )
            ),
        ),
    ]

    _, visual, _, _ = birth._merge_plugin_influences(deltas)
    assert visual.color_shifts["trim"].hex_override == "#BBBBBB"


@pytest.mark.asyncio
async def test_resolve_glow_rule_falls_back_to_highest_weight(monkeypatch):
    async def fake_semantic_merge(candidates, direction):
        raise RuntimeError("boom")

    monkeypatch.setattr(birth, "_semantic_merge_glow_rule", fake_semantic_merge)

    resolved = await birth._resolve_glow_rule(
        [("low", 0.2), ("high", 0.8)],
        "direction",
    )
    assert resolved == "high"


@pytest.mark.asyncio
async def test_birth_vibemon_derives_visual_dna_and_uses_semantic_merge(monkeypatch):
    async def fake_generate_creature(name, description, visual_dna):
        return Creature(
            name=name,
            anatomy=Anatomy(torso="compact"),
            colors=[ColorZone(region="primary", description="azure", hex="#0099FF")],
            glow_rule=visual_dna.glow_rule or "none",
        )

    async def fake_semantic_merge(candidates, direction):
        return "merged glow"

    monkeypatch.setattr(birth, "generate_creature", fake_generate_creature)
    monkeypatch.setattr(birth, "_semantic_merge_glow_rule", fake_semantic_merge)

    provider = FakeProvider(
        name="p1",
        intensity=0.5,
        delta=Delta(
            delta_stats={"attack": 60, "speed": 30},
            delta_visual=VisualDelta(
                color_shifts={"primary": ColorShift(hue_rotation=12.0)},
                glow_rule_override="spark only on edges",
            ),
            delta_description="from plugin",
        ),
    )
    context = Context(
        birth_seed="seed",
        timestamp="2026-04-20T00:00:00+00:00",
        source_data={"spotify": SourceData(provider_id="spotify", payload={})},
        enabled_providers=["p1"],
    )

    vibemon = await birth.birth_vibemon(
        name="Pulsemoth",
        user_description="swift and sharp",
        context=context,
        providers=[provider],
    )

    assert vibemon.base_attack == 30
    assert vibemon.base_speed == 15
    assert vibemon.description == "swift and sharp\nfrom plugin"
    assert vibemon.visual_dna is not None
    assert vibemon.visual_dna.glow_rule == "merged glow"
    assert vibemon.visual_dna.stat_weights["attack"] == 30
