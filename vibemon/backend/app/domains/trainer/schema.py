"""Trainer read models for HTTP and other public interfaces."""

from app.core.ids import TrainerIdT
from app.core.schema import Schema


class PublicTrainerRead(Schema):
    """Trainer identity returned to authenticated clients."""

    id: TrainerIdT
    username: str
    crew_count: int = 0
