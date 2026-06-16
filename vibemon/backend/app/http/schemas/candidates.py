"""HTTP bodies for candidate generation and review."""

import uuid

from app.core.schema import Schema


class CandidateGenerateBody(Schema):
    providers: tuple[str, ...]
    latitude: float | None = None
    longitude: float | None = None


class CandidateAdoptBody(Schema):
    nickname: str | None = None
    release_vibemon_id: uuid.UUID | None = None
