"""Generation ports for infrastructure adapters."""

from typing import Protocol
import uuid


class TrainerSecrets(Protocol):
    """Read trainer-scoped secrets without coupling domains to storage."""

    async def get(self, trainer_id: uuid.UUID, kind: str) -> str | None: ...
