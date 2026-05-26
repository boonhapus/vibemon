"""Unit tests for Overpass water geometry distance."""

from app.providers.biome.water.overpass import utils as overpass_utils


def test_point_to_segment_uses_nearest_point_on_line() -> None:
    # Point near the middle of a short north-south segment east of Chicago.
    distance_km = overpass_utils.point_to_segment_km(41.8781, -87.6298, 41.8700, -87.6200, 41.8900, -87.6200)
    endpoint_km = overpass_utils.haversine_km(41.8781, -87.6298, 41.8700, -87.6200)
    assert distance_km < endpoint_km
    assert distance_km < 1.5


def test_nearest_distance_prefers_polyline_over_center() -> None:
    # A long east-west shoreline segment should beat a distant center point.
    shoreline = [(41.8780, -87.7000), (41.8780, -87.6000)]
    shoreline_km = overpass_utils.nearest_distance_km(41.8781, -87.6298, shoreline)
    center_km = overpass_utils.haversine_km(41.8781, -87.6298, 41.8780, -87.6500)
    assert shoreline_km < center_km
    assert shoreline_km < 1.0


def test_nearest_element_uses_geometry_field() -> None:
    elements = [
        {
            "type": "way",
            "tags": {"natural": "water", "water": "lake"},
            "geometry": [
                {"lat": 41.8780, "lon": -87.7000},
                {"lat": 41.8780, "lon": -87.6000},
            ],
        },
        {
            "type": "way",
            "tags": {"natural": "water", "water": "lake"},
            "center": {"lat": 41.8780, "lon": -87.4000},
        },
    ]
    nearest = overpass_utils.nearest_element(41.8781, -87.6298, elements, marine=True)
    assert nearest is not None
    assert nearest[1] == "lake"
    assert nearest[0] < 1.0


def test_inland_feature_returns_lake_tag() -> None:
    assert overpass_utils.inland_feature({"natural": "water", "water": "lake"}) == "lake"
