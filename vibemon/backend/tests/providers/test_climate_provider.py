from typing import cast
import collections

from app.domains.move import universal
from app.providers.climate.provider import ClimateProvider


def test_calculate_intensity_handles_missing_visibility() -> None:
    daily = cast(
        dict[str, list[float | None]],
        {
            "temperature_2m_max": [20.0, 22.0, 18.0],
            "temperature_2m_min": [8.0, 10.0, 6.0],
            "precipitation_sum": [1.5, 0.0, 2.0],
            "wind_gusts_10m_max": [30.0, 25.0, 35.0],
            "cape_mean": [100.0, 80.0, 120.0],
            "visibility_mean": [15000.0, None, 12000.0],
        },
    )

    intensity = ClimateProvider().calculate_intensity(daily, index=-1)

    assert 0.0 <= intensity <= 1.0


def test_climate_move_catalog_has_fifteen_moves_per_exposed_element() -> None:
    provider = ClimateProvider()
    exposed_types = set(provider.get_exposed_elements())

    catalog_types = {move.type for move in provider.moves()}
    move_counts = collections.Counter(move.type for move in provider.moves())

    assert catalog_types <= exposed_types
    assert move_counts == {element: 15 for element in exposed_types}


def test_climate_selectable_moves_include_shared_universal_moves_once() -> None:
    provider = ClimateProvider()

    universal_ids = {move.id for move in universal.moves()}
    selectable_ids = [move.id for move in provider.selectable_moves(level=99)]

    assert universal_ids == {"universal.snap_strike", "universal.tackle"}
    assert universal_ids <= set(selectable_ids)
    assert len(selectable_ids) == len(set(selectable_ids))
    assert len(selectable_ids) == len(provider.moves()) + len(universal.moves())
