from app.domains.move.types import VibemonTypeT
from app.providers.celestial.provider import CelestialProvider


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
