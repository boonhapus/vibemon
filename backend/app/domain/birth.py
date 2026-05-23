"""Birth-domain schemas and deterministic seed helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any
import asyncio
import datetime as dt
import hashlib
import json
import random

import pydantic

from app.plugins.provider import VibeProvider

if TYPE_CHECKING:
    from app.domain.vibemon import Affinity


class Schema(pydantic.BaseModel):
    """Mutable domain data object base. Use for runtime/lifecycle-shaped data."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )


class FrozenSchema(pydantic.BaseModel):
    """Immutable value object base. Use for definitions and event/log records."""

    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        frozen=True,
    )


class BirthSnapshot(FrozenSchema):
    """Captured provider payloads used to synthesize affinities."""

    provider_payloads: dict[str, dict[str, Any]]

    async def regenerate(self, providers: Iterable[VibeProvider], seed: BirthSeed) -> Iterable[Affinity]:
        """Given a seed + captured payloads, create affinities without new API calls."""
        providers_by_name = {provider.name: provider for provider in providers}

        missing_provider_ids = [
            provider_id for provider_id in self.provider_payloads if provider_id not in providers_by_name
        ]

        if missing_provider_ids:
            missing = ", ".join(sorted(set(missing_provider_ids)))
            raise ValueError(f"Missing provider implementations for captured snapshot: {missing}")

        affinities = await asyncio.gather(
            *(
                providers_by_name[provider_id].synthesize(seed, self.provider_payloads[provider_id])
                for provider_id in sorted(self.provider_payloads)
            )
        )
        return affinities


class BirthSeed(FrozenSchema):
    """Reproducible input used to fetch provider payloads."""

    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    providers: list[VibeProvider]

    @pydantic.field_validator("timestamp")
    @classmethod
    def _normalize_to_utc(cls, v: dt.datetime) -> dt.datetime:
        """Ensure timestamp is aware UTC. SQLite strips tz, so naive values must round-trip stably."""
        if v.tzinfo is None:
            return v.replace(tzinfo=dt.UTC)
        return v.astimezone(dt.UTC)

    @property
    def datestamp(self) -> dt.date:
        """Get the date of the birth seed."""
        return self.timestamp.date()

    @staticmethod
    def _hash_seed_material(seed_material: dict[str, Any]) -> int:
        encoded = json.dumps(seed_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return int.from_bytes(hashlib.sha256(encoded).digest(), "big")

    @property
    def _rng_seed_material(self) -> dict[str, Any]:
        return {
            "geo_coords": list(self.geo_coords),
            "timestamp": self.timestamp.isoformat(timespec="microseconds"),
        }

    @property
    def rng_seed(self) -> int:
        """Stable integer seed derived from birth inputs."""
        return self._hash_seed_material(self._rng_seed_material)

    def rng_seed_for(self, namespace: str) -> int:
        """Stable integer seed for one deterministic birth subsystem."""
        return self._hash_seed_material(
            {
                "birth_seed": self._rng_seed_material,
                "namespace": namespace,
            }
        )

    def rng(self, namespace: str) -> random.Random:
        """Create a fresh deterministic RNG for one birth subsystem."""
        return random.Random(self.rng_seed_for(namespace))

    async def fetch_snapshot(self) -> BirthSnapshot:
        """Fetch provider payloads for this seed."""
        snapshots = await asyncio.gather(*(provider.fetch(self) for provider in self.providers))
        return BirthSnapshot(provider_payloads={p.name: s for p, s in zip(self.providers, snapshots, strict=True)})

    async def regenerate(self) -> Iterable[Affinity]:
        """Fetch provider payloads, then synthesize affinities from that snapshot."""
        snapshot = await self.fetch_snapshot()
        return await snapshot.regenerate(self.providers, self)
