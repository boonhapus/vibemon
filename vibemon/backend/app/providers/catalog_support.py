"""Shared catalog constants and unimplemented provider base."""

from typing import ClassVar

from app.core.errors import ProviderNotImplemented
from app.domains.generation.affinity import Affinity
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider

GEOLOCATION_REQUIREMENT = catalog.GeolocationRequirement(
    id="geolocation",
    label="Location access",
    description="Uses your coordinates for signals at birth time.",
)


class UnimplementedProvider(VibeProvider[providers_schema.UnimplementedPayload]):
    """Catalog-only provider stub until fetch and synthesize are implemented."""

    implemented: ClassVar[bool] = False
    payload_type = providers_schema.UnimplementedPayload
    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = []

    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> providers_schema.UnimplementedPayload:
        raise ProviderNotImplemented(f"Provider {self.name!r} is not implemented yet.")

    async def synthesize(
        self,
        seed: BirthSeed,
        payload: providers_schema.UnimplementedPayload,
    ) -> Affinity:
        raise ProviderNotImplemented(f"Provider {self.name!r} is not implemented yet.")
