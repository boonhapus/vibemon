import asyncio

import pytest

from app.plugins.protocol import (
    ColorShift,
    Context,
    DataProvider,
    Delta,
    SourceData,
    VisualDelta,
    clamp_stat,
    merge_deltas,
)
from app.plugins.climate.provider import ClimateProvider
from app.plugins.spotify.provider import SpotifyProvider


class TestColorShiftClamping:
    def test_hue_rotation_clamped(self):
        cs = ColorShift(hue_rotation=50.0)
        assert cs.hue_rotation == 30.0

    def test_hue_rotation_clamped_negative(self):
        cs = ColorShift(hue_rotation=-50.0)
        assert cs.hue_rotation == -30.0

    def test_lightness_clamped(self):
        cs = ColorShift(lightness_adjust=0.5)
        assert cs.lightness_adjust == 0.15

    def test_lightness_clamped_negative(self):
        cs = ColorShift(lightness_adjust=-0.5)
        assert cs.lightness_adjust == -0.15


class TestClampStat:
    def test_within_range(self):
        assert clamp_stat(128) == 128

    def test_below_zero(self):
        assert clamp_stat(-10) == 0

    def test_above_255(self):
        assert clamp_stat(300) == 255


class TestMergeDeltas:
    def test_neutral_intensity_no_stat_change(self):
        base = {"max_hp": 100, "attack": 50}
        delta = Delta(delta_stats={"max_hp": 80, "attack": 40})
        final, visual, _ = merge_deltas(base, [(0.0, delta)])
        assert final == {"max_hp": 100, "attack": 50}

    def test_full_intensity_applies_deltas(self):
        base = {"max_hp": 100, "attack": 50}
        delta = Delta(delta_stats={"max_hp": 10, "attack": 20})
        final, visual, _ = merge_deltas(base, [(1.0, delta)])
        assert final == {"max_hp": 110, "attack": 70}

    def test_stat_clamped_to_255(self):
        base = {"max_hp": 250}
        delta = Delta(delta_stats={"max_hp": 100})
        final, _, _ = merge_deltas(base, [(1.0, delta)])
        assert final["max_hp"] == 255

    def test_stat_clamped_to_0(self):
        base = {"attack": 10}
        delta = Delta(delta_stats={"attack": -50})
        final, _, _ = merge_deltas(base, [(1.0, delta)])
        assert final["attack"] == 0

    def test_multiple_providers_accumulate(self):
        base = {"speed": 50}
        d1 = Delta(delta_stats={"speed": 20})
        d2 = Delta(delta_stats={"speed": 15})
        final, _, _ = merge_deltas(base, [(1.0, d1), (1.0, d2)])
        assert final["speed"] == 85

    def test_visual_color_shifts_merge(self):
        d1 = Delta(
            delta_visual=VisualDelta(
                color_shifts={"primary": ColorShift(hue_rotation=10.0)}
            )
        )
        d2 = Delta(
            delta_visual=VisualDelta(
                color_shifts={"primary": ColorShift(hue_rotation=15.0)}
            )
        )
        _, visual, _ = merge_deltas({}, [(1.0, d1), (1.0, d2)])
        assert visual.color_shifts["primary"].hue_rotation == 25.0

    def test_hex_override_last_writer_wins(self):
        d1 = Delta(
            delta_visual=VisualDelta(
                color_shifts={"primary": ColorShift(hex_override="#FF0000")}
            )
        )
        d2 = Delta(
            delta_visual=VisualDelta(
                color_shifts={"primary": ColorShift(hex_override="#00FF00")}
            )
        )
        _, visual, _ = merge_deltas({}, [(1.0, d1), (1.0, d2)])
        assert visual.color_shifts["primary"].hex_override == "#00FF00"

    def test_glow_rule_override_last_writer_wins(self):
        d1 = Delta(delta_visual=VisualDelta(glow_rule_override="rule_a"))
        d2 = Delta(delta_visual=VisualDelta(glow_rule_override="rule_b"))
        _, visual, _ = merge_deltas({}, [(1.0, d1), (1.0, d2)])
        assert visual.glow_rule_override == "rule_b"


class TestProtocolConformance:
    def test_climate_is_data_provider(self):
        assert isinstance(ClimateProvider(), DataProvider)

    def test_spotify_is_data_provider(self):
        assert isinstance(SpotifyProvider(), DataProvider)


@pytest.mark.asyncio
class TestClimateProviderDeterminism:
    async def test_same_context_same_output(self):
        provider = ClimateProvider()
        ctx = Context(
            birth_seed="seed_abc",
            timestamp="2026-04-17T14:30:00+00:00",
            location="40.7128,-74.0060",
            enabled_providers=["climate"],
        )
        r1 = await provider.contribute(ctx)
        r2 = await provider.contribute(ctx)
        assert r1 == r2

    async def test_intensity_is_zero(self):
        provider = ClimateProvider()
        ctx = Context(birth_seed="x", timestamp="2026-01-01T00:00:00+00:00")
        assert await provider.intensity(ctx) == 0.0

    async def test_stat_deltas_are_nonzero(self):
        provider = ClimateProvider()
        ctx = Context(
            birth_seed="y",
            timestamp="2026-06-15T12:30:45+00:00",
            location="51.5,-0.1",
        )
        delta = await provider.contribute(ctx)
        assert any(v != 0 for v in delta.delta_stats.values())

    async def test_delta_level_is_zero(self):
        provider = ClimateProvider()
        ctx = Context(birth_seed="z", timestamp="2026-01-01T00:00:00+00:00")
        delta = await provider.contribute(ctx)
        assert delta.delta_level == 0


@pytest.mark.asyncio
class TestSpotifyProvider:
    async def test_no_source_data_returns_empty_delta(self):
        provider = SpotifyProvider()
        ctx = Context(
            birth_seed="s1",
            timestamp="2026-04-17T10:00:00+00:00",
            enabled_providers=["spotify"],
        )
        delta = await provider.contribute(ctx)
        assert delta.delta_stats == {}
        assert delta.delta_visual.color_shifts == {}

    async def test_with_source_data_produces_visual(self):
        provider = SpotifyProvider()
        ctx = Context(
            birth_seed="s2",
            timestamp="2026-04-17T10:00:00+00:00",
            enabled_providers=["spotify"],
            source_data={
                "spotify": SourceData(
                    provider_id="spotify",
                    payload={
                        "mood": "energetic",
                        "listening_minutes": 60,
                        "track_count": 10,
                    },
                )
            },
        )
        delta = await provider.contribute(ctx)
        assert "primary" in delta.delta_visual.color_shifts
        assert delta.delta_visual.color_shifts["primary"].hue_rotation == 10.0

    async def test_intensity_is_zero(self):
        provider = SpotifyProvider()
        ctx = Context(birth_seed="s3", timestamp="2026-01-01T00:00:00+00:00")
        assert await provider.intensity(ctx) == 0.0


@pytest.mark.asyncio
class TestEndToEndMerge:
    async def test_both_providers_opted_in(self):
        climate = ClimateProvider()
        spotify = SpotifyProvider()

        ctx = Context(
            birth_seed="e2e_seed",
            timestamp="2026-04-17T14:30:00+00:00",
            location="40.7128,-74.0060",
            enabled_providers=["climate", "spotify"],
            source_data={
                "spotify": SourceData(
                    provider_id="spotify",
                    payload={
                        "mood": "calm",
                        "listening_minutes": 30,
                        "track_count": 5,
                    },
                )
            },
        )

        providers = [climate, spotify]
        deltas: list[tuple[float, Delta]] = []
        for p in providers:
            if p.name in ctx.enabled_providers:
                intensity = await p.intensity(ctx)
                delta = await p.contribute(ctx)
                deltas.append((intensity, delta))

        base_stats = {
            "max_hp": 100,
            "attack": 50,
            "defense": 50,
            "sp_attack": 50,
            "sp_defense": 50,
            "speed": 50,
        }
        final_stats, visual, _ = merge_deltas(base_stats, deltas)

        # intensity is 0 for both in MVP, so stats unchanged
        assert final_stats == base_stats
        assert visual.glow_rule_override is None
