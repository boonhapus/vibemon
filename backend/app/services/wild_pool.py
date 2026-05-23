"""Wild encounter eligibility query and geography bucketing."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app import models, types
from app.services import wild_geography

GEOHASH_PRECISION = 5


class WildPoolService:
    """Fetch eligible wild Vibemon IDs using geographic bucket expansion."""

    def bucket_expansion(self, *, latitude: float, longitude: float) -> list[set[str]]:
        center = wild_geography.geohash_encode(latitude, longitude, precision=GEOHASH_PRECISION)
        return [
            {center},
            wild_geography.geohash_ring(center, ring=1),
            wild_geography.geohash_ring(center, ring=2),
        ]

    async def list_eligible_wild_ids(
        self,
        sess: AsyncSession,
        *,
        latitude: float,
        longitude: float,
        limit: int,
    ) -> list[uuid.UUID]:
        if limit <= 0:
            return []
        rows = (
            await sess.execute(
                sa.select(models.Vibemon.id, models.BirthSeed.geo_coords)
                .join(models.BirthSnapshot, models.BirthSnapshot.id == models.Vibemon.birth_snapshot_id)
                .join(models.BirthSeed, models.BirthSeed.id == models.BirthSnapshot.birth_seed_id)
                .where(*self._eligible_wild_predicates())
                .order_by(models.Vibemon.wild_entered_at.desc().nullslast(), models.Vibemon.id)
            )
        ).all()
        by_bucket: dict[str, list[uuid.UUID]] = {}
        for vibemon_id, geo_coords in rows:
            if len(geo_coords) < 2:
                continue
            bucket = wild_geography.geohash_encode(
                float(geo_coords[0]),
                float(geo_coords[1]),
                precision=GEOHASH_PRECISION,
            )
            by_bucket.setdefault(bucket, []).append(vibemon_id)
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

    def _eligible_wild_predicates(self) -> tuple[sa.ColumnElement[bool], ...]:
        pending_review_exists = sa.exists(
            sa.select(1).where(
                models.CandidateReview.vibemon_id == models.Vibemon.id,
                models.CandidateReview.status == types.CandidateReviewStatusT.PENDING.value,
            )
        )
        return (
            models.Vibemon.disposition == types.VibemonDispositionT.WILD.value,
            models.Vibemon.expired_at.is_(None),
            ~pending_review_exists,
        )
