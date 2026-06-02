"""Deterministic Vibemon birth seed helpers."""

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any
import asyncio
import datetime as dt
import hashlib
import json
import random
import uuid

from astral import Observer
from astral.sun import sun
import pydantic

from app.core.schema import FrozenSchema

from . import types
from .ports import TrainerSecrets
from .snapshot import BirthSnapshot

if TYPE_CHECKING:
    from .affinity import Affinity


class BirthSeed(FrozenSchema):
    """Reproducible input used to fetch provider payloads."""

    timestamp: dt.datetime
    geo_coords: tuple[float, float]
    trainer_id: uuid.UUID
    local_timezone: dt.timezone = dt.UTC
    providers: list[Any]

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

    @property
    def local_time(self) -> dt.datetime:
        """Birth instant in the seed's local timezone."""
        return self.timestamp.astimezone(self.local_timezone)

    @property
    def solar_phase(self) -> types.SolarPhase:
        """Local solar-time phase derived from timestamp and coordinates."""
        latitude, longitude = self.geo_coords
        observer = Observer(latitude=latitude, longitude=longitude)

        try:
            solar = sun(observer, date=self.local_time.date(), tzinfo=self.local_timezone)
        except ValueError:
            return types.SolarPhase.NIGHT if abs(latitude) > 66.0 else types.SolarPhase.DAY

        if self.local_time < solar["dawn"]:
            return types.SolarPhase.NIGHT

        if self.local_time < solar["sunrise"]:
            return types.SolarPhase.DAWN

        if self.local_time < solar["sunset"]:
            return types.SolarPhase.DAY

        if self.local_time < solar["dusk"]:
            return types.SolarPhase.DUSK

        return types.SolarPhase.NIGHT

    @staticmethod
    def _hash_seed_material(seed_material: dict[str, Any]) -> int:
        encoded = json.dumps(seed_material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return int.from_bytes(hashlib.sha256(encoded).digest(), "big")

    @property
    def _rng_seed_material(self) -> dict[str, Any]:
        return {
            "geo_coords": list(self.geo_coords),
            "timestamp": self.timestamp.isoformat(timespec="microseconds"),
            "trainer_id": str(self.trainer_id),
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

    async def fetch_snapshot(self, secrets: TrainerSecrets | None = None) -> BirthSnapshot:
        """Fetch provider payloads for this seed."""
        snapshots = await asyncio.gather(*(provider.fetch(self, secrets=secrets) for provider in self.providers))
        return BirthSnapshot(
            provider_payloads={
                provider.name: provider.serialize_payload(payload)
                for provider, payload in zip(self.providers, snapshots, strict=True)
            }
        )

    async def regenerate(self, secrets: TrainerSecrets | None = None) -> Iterable[Affinity]:
        """Fetch provider payloads, then synthesize affinities from that snapshot."""
        snapshot = await self.fetch_snapshot(secrets)
        return await snapshot.regenerate(self.providers, self)
