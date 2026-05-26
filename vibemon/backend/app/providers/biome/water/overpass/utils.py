"""Geometry helpers for Overpass water proximity."""

from typing import Any
import itertools as it
import math


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


def _to_xy(latitude: float, longitude: float, *, ref_lat: float) -> tuple[float, float]:
    scale = math.cos(math.radians(ref_lat))
    return longitude * scale, latitude


def point_to_segment_km(
    point_lat: float,
    point_lon: float,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> float:
    ref_lat = point_lat
    point_x, point_y = _to_xy(point_lat, point_lon, ref_lat=ref_lat)
    start_x, start_y = _to_xy(start_lat, start_lon, ref_lat=ref_lat)
    end_x, end_y = _to_xy(end_lat, end_lon, ref_lat=ref_lat)
    delta_x = end_x - start_x
    delta_y = end_y - start_y
    if delta_x == 0.0 and delta_y == 0.0:
        return haversine_km(point_lat, point_lon, start_lat, start_lon)

    projection = ((point_x - start_x) * delta_x + (point_y - start_y) * delta_y) / (delta_x**2 + delta_y**2)
    clamped = max(0.0, min(1.0, projection))
    closest_lat = start_y + clamped * delta_y
    closest_lon = (start_x + clamped * delta_x) / math.cos(math.radians(ref_lat))
    return haversine_km(point_lat, point_lon, closest_lat, closest_lon)


def _element_points(element: dict[str, Any]) -> list[tuple[float, float]]:
    if element.get("type") == "node":
        lat, lon = element.get("lat"), element.get("lon")
        if lat is None or lon is None:
            return []
        return [(float(lat), float(lon))]

    geometry = element.get("geometry")
    if isinstance(geometry, list) and geometry:
        points: list[tuple[float, float]] = []
        for node in geometry:
            lat, lon = node.get("lat"), node.get("lon")
            if lat is None or lon is None:
                continue
            points.append((float(lat), float(lon)))
        return points

    center = element.get("center") or {}
    lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return []
    return [(float(lat), float(lon))]


def nearest_distance_km(latitude: float, longitude: float, points: list[tuple[float, float]]) -> float:
    if not points:
        return math.inf
    if len(points) == 1:
        return haversine_km(latitude, longitude, points[0][0], points[0][1])

    best = math.inf
    for start, end in it.pairwise(points):
        best = min(best, point_to_segment_km(latitude, longitude, start[0], start[1], end[0], end[1]))
    if points[0] != points[-1]:
        start, end = points[-1], points[0]
        best = min(best, point_to_segment_km(latitude, longitude, start[0], start[1], end[0], end[1]))
    return best


def _marine_feature(tags: dict[str, str]) -> str:
    if tags.get("water") == "lake":
        return "lake"
    return tags.get("natural") or tags.get("place") or "unknown"


def inland_feature(tags: dict[str, str]) -> str:
    if waterway := tags.get("waterway"):
        return waterway
    if tags.get("natural") == "water":
        return tags.get("water") or "water"
    return tags.get("water") or "water"


def nearest_element(
    latitude: float,
    longitude: float,
    elements: list[dict[str, Any]],
    *,
    marine: bool,
) -> tuple[float, str] | None:
    nearest: tuple[float, str] | None = None
    for element in elements:
        points = _element_points(element)
        if not points:
            continue
        distance_km = nearest_distance_km(latitude, longitude, points)
        tags = element.get("tags") or {}
        if not isinstance(tags, dict):
            continue
        feature = _marine_feature(tags) if marine else inland_feature(tags)
        if nearest is None or distance_km < nearest[0]:
            nearest = (distance_km, feature)
    return nearest
