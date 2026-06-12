"""Generation ports for infrastructure adapters."""

from typing import TYPE_CHECKING, Any, Protocol
import uuid

if TYPE_CHECKING:
    from app.domains.generation.affinity import Affinity
    from app.domains.generation.seed import BirthSeed


class TrainerSecrets(Protocol):
    """Read trainer-scoped secrets without coupling domains to storage."""

    async def get(self, trainer_id: uuid.UUID, kind: str) -> str | None: ...


class BirthProvider(Protocol):
    """Narrow port for live fetch and snapshot replay during Vibemon birth."""

    name: str

    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> Any: ...

    async def synthesize(self, seed: BirthSeed, payload: Any) -> Affinity: ...

    def serialize_payload(self, payload: Any) -> dict[str, Any]: ...

    def parse_payload(self, raw: dict[str, Any]) -> Any: ...
