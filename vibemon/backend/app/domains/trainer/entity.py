"""Trainer-domain entity schemas."""

import uuid

import pydantic

from app.core.ids import TrainerIdT
from app.core.schema import Schema
from app.domains.vibemon.entity import Vibemon


class Trainer(Schema):
    id: TrainerIdT = pydantic.Field(default_factory=uuid.uuid7)
    username: str
    crew: list[Vibemon] = pydantic.Field(default_factory=list)
