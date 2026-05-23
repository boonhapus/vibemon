"""Wild encounter eligibility query and geography bucketing."""

from __future__ import annotations

import uuid

import pydantic

from app.core.schema import FrozenSchema
from app.domains.encounter import geography as wild_geography

GEOHASH_PRECISION = 5


class WildPoolCandidate(FrozenSchema):
    vibemon_id: uuid.UUID
    geo_coords: tuple[float, ...]

    @pydantic.field_validator("geo_coords", mode="before")
    @classmethod
    def _coerce_geo_coords_tuple(cls, value: object) -> object:
        if isinstance(value, list):
            return tuple(value)
        return value


class WildPoolService:
    """Order eligible wild Vibemon IDs using geographic bucket expansion."""

    def bucket_expansion(self, *, latitude: float, longitude: float) -> list[set[str]]:
        center = wild_geography.geohash_encode(latitude, longitude, precision=GEOHASH_PRECISION)
        return [
            {center},
            wild_geography.geohash_ring(center, ring=1),
            wild_geography.geohash_ring(center, ring=2),
        ]

    def select_eligible_wild_ids(
        self,
        candidates: list[WildPoolCandidate],
        *,
        latitude: float,
        longitude: float,
        limit: int,
    ) -> list[uuid.UUID]:
        if limit <= 0:
            return []
        by_bucket: dict[str, list[uuid.UUID]] = {}
        for candidate in candidates:
            if len(candidate.geo_coords) < 2:
                continue
            bucket = wild_geography.geohash_encode(
                candidate.geo_coords[0],
                candidate.geo_coords[1],
                precision=GEOHASH_PRECISION,
            )
            by_bucket.setdefault(bucket, []).append(candidate.vibemon_id)
        out: list[uuid.UUID] = []
        seen: set[uuid.UUID] = set()
        for buckets in self.bucket_expansion(latitude=latitude, longitude=longitude):
            for bucket in buckets:
                for vibemon_id in by_bucket.get(bucket, []):
                    if vibemon_id in seen:
                        continue
                    seen.add(vibemon_id)
                    out.append(vibemon_id)
                    if len(out) >= limit:
                        return out
        return out
