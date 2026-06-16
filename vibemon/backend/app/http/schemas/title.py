"""HTTP read models for the title screen."""

import uuid

from app.core.schema import Schema


class TitleMonRead(Schema):
    id: uuid.UUID
    reference_url: str


class TitleMonListRead(Schema):
    mons: tuple[TitleMonRead, ...]
