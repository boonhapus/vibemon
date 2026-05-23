import collections

from app.domains.move import universal
from app.providers.climate.provider import ClimateProvider


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
    selectable_ids = [move.id for move in provider.selectable_moves()]

    assert universal_ids == {"universal.snap_strike", "universal.tackle"}
    assert universal_ids <= set(selectable_ids)
    assert len(selectable_ids) == len(set(selectable_ids))
    assert len(selectable_ids) == len(provider.moves()) + len(universal.moves())
