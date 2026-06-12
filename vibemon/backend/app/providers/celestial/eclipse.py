"""Eclipse-season detection from Sun and lunar node longitudes."""

from app.core.math import angular_distance


def in_eclipse_season(
    sun_longitude: float,
    *,
    ascending_node_longitude: float,
    descending_node_longitude: float,
    orb_deg: float = 15.0,
) -> bool:
    return (
        min(
            angular_distance(sun_longitude, ascending_node_longitude),
            angular_distance(sun_longitude, descending_node_longitude),
        )
        <= orb_deg
    )
