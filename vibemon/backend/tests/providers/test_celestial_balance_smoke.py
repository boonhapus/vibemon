from scripts.rehearse_celestial_balance import (
    CURATED_CASES,
    TWILIGHT_EDGE_BAND_POSITION,
    TWILIGHT_EDGE_CASES,
    MatrixScope,
    evaluate_case,
    iter_matrix_cases,
    phase_ok,
    run_matrix,
    summarize,
)
import pytest

from app.domains.generation import types as generation_types
from app.domains.move.types import VibemonTypeT
from app.providers.celestial.provider import CelestialProvider


@pytest.mark.asyncio
async def test_curated_celestial_balance_meets_phase_semantics() -> None:
    provider = CelestialProvider()
    rows: list[dict[str, object]] = []
    for label, city, phase, date in CURATED_CASES:
        row = await evaluate_case(label=label, city=city, phase=phase, date=date, provider=provider)
        assert row["phase_match"] is True
        rows.append(row)

    summary = summarize(tuple(rows))
    assert summary["phase_ok_pct"] >= 80.0
    assert summary["dawn_fairy_psychic_pct"] == 100.0
    assert summary["deep_night_dark_ghost_pct"] == 100.0
    assert summary["deep_night_fire_primary_pct"] == 0.0


@pytest.mark.asyncio
async def test_full_celestial_balance_matrix_meets_success_criteria() -> None:
    rows, summary = await run_matrix(scope=MatrixScope.FULL)
    assert len(rows) == 120
    criteria = summary["success_criteria"]
    assert criteria["phase_ok_at_least_80"] is True
    assert criteria["dawn_at_least_70"] is True
    assert criteria["dusk_at_least_70"] is True
    assert criteria["deep_night_dark_ghost_at_least_75"] is True
    assert criteria["dual_rate_in_band_45_85"] is True
    assert summary["deep_night_fire_primary_pct"] == 0.0
    duplicate_profiles = summary.get("duplicate_profiles", [])
    assert all(profile["count"] <= 4 for profile in duplicate_profiles)


def test_phase_ok_accepts_native_secondary_type() -> None:
    assert phase_ok(
        generation_types.SolarPhase.DAWN,
        (VibemonTypeT.FIRE, VibemonTypeT.PSYCHIC),
    )
    assert phase_ok(
        generation_types.SolarPhase.NIGHT,
        (VibemonTypeT.DARK, VibemonTypeT.FIRE),
    )
    assert not phase_ok(
        generation_types.SolarPhase.DUSK,
        (VibemonTypeT.PSYCHIC, VibemonTypeT.WATER),
    )


def test_matrix_case_count() -> None:
    assert len(iter_matrix_cases(MatrixScope.FULL)) == 120
    assert len(iter_matrix_cases(MatrixScope.CURATED)) == 18


@pytest.mark.asyncio
async def test_twilight_edge_cases_surface_moon_and_season_primaries() -> None:
    provider = CelestialProvider()
    expected_primary = {
        "Tokyo dawn edge": VibemonTypeT.GRASS.value,
        "London dusk edge": VibemonTypeT.ICE.value,
        "Mumbai dusk edge": VibemonTypeT.WATER.value,
    }

    for label, city, phase, date in TWILIGHT_EDGE_CASES:
        row = await evaluate_case(
            label=label,
            city=city,
            phase=phase,
            date=date,
            provider=provider,
            band_position=TWILIGHT_EDGE_BAND_POSITION,
        )
        assert row["phase_match"] is True
        assert row["twilight_edge"] is True
        assert row["fused_elements"][0] == expected_primary[label]


def test_pick_celestial_elements_uses_sky_for_primary() -> None:
    sky = {VibemonTypeT.GHOST: 1.0, VibemonTypeT.DARK: 0.9}
    chart = {VibemonTypeT.FIRE: 1.0}

    elements, _rankings = CelestialProvider._pick_celestial_elements(
        sky_rankings=sky,
        chart_rankings=chart,
        chart_dominant=VibemonTypeT.FIRE,
    )

    assert elements[0] in {VibemonTypeT.GHOST, VibemonTypeT.DARK}


def test_pick_celestial_elements_uses_chart_dominant_for_secondary() -> None:
    sky = {VibemonTypeT.GHOST: 1.0}
    chart = {VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.75}

    elements, _rankings = CelestialProvider._pick_celestial_elements(
        sky_rankings=sky,
        chart_rankings=chart,
        chart_dominant=VibemonTypeT.FIRE,
    )

    assert elements == (VibemonTypeT.GHOST, VibemonTypeT.FIRE)


def test_pick_celestial_elements_scattered_chart_single_types() -> None:
    sky = {VibemonTypeT.GHOST: 1.0}
    chart = {VibemonTypeT.FIRE: 1.0, VibemonTypeT.WATER: 0.75, VibemonTypeT.FLYING: 0.5}

    elements, _rankings = CelestialProvider._pick_celestial_elements(
        sky_rankings=sky,
        chart_rankings=chart,
        chart_dominant=None,
    )

    assert elements == (VibemonTypeT.GHOST,)


def test_pick_celestial_elements_dominant_matching_primary_single_types() -> None:
    sky = {VibemonTypeT.FIRE: 1.0}
    chart = {VibemonTypeT.FIRE: 1.75, VibemonTypeT.WATER: 0.5}

    elements, _rankings = CelestialProvider._pick_celestial_elements(
        sky_rankings=sky,
        chart_rankings=chart,
        chart_dominant=VibemonTypeT.FIRE,
    )

    assert elements == (VibemonTypeT.FIRE,)
