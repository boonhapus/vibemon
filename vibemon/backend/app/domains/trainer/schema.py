"""Trainer read models for HTTP and other public interfaces."""

from app.core.ids import TrainerIdT
from app.core.schema import Schema


class PublicTrainerRead(Schema):
    """Trainer identity returned to authenticated clients."""

    id: TrainerIdT
    username: str
    crew_count: int = 0
    reference_url: str | None = None
    reference_selected_revision: int | None = None
    reference_max_revision: int | None = None
