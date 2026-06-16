from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING, Any
import asyncio

from app.core.schema import FrozenSchema
from app.domains.generation.ports import BirthProvider

LEARNSET_PAYLOAD_KEY = "__learnset__"

if TYPE_CHECKING:
    from app.domains.generation.affinity import Affinity
    from app.domains.generation.seed import BirthSeed


class BirthSnapshot(FrozenSchema):
    """Captured provider payloads used to synthesize affinities."""

    provider_payloads: dict[str, dict[str, Any]]

    async def regenerate(
        self,
        providers: Sequence[BirthProvider],
        seed: BirthSeed,
    ) -> Iterable[Affinity]:
        """Given a seed + captured payloads, create affinities without new API calls."""
        providers_by_name = {provider.name: provider for provider in providers}

        missing_provider_ids = [
            provider_id
            for provider_id in self.provider_payloads
            if provider_id not in providers_by_name and provider_id != LEARNSET_PAYLOAD_KEY
        ]

        if missing_provider_ids:
            missing = ", ".join(sorted(set(missing_provider_ids)))
            raise ValueError(f"Missing provider implementations for captured snapshot: {missing}")

        affinities = await asyncio.gather(
            *(
                providers_by_name[provider_id].synthesize(
                    seed,
                    providers_by_name[provider_id].parse_payload(self.provider_payloads[provider_id]),
                )
                for provider_id in sorted(self.provider_payloads)
                if provider_id != LEARNSET_PAYLOAD_KEY
            )
        )
        return affinities
