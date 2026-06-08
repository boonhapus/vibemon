"""HTTP request and response bodies."""

from typing import Annotated

import pydantic

from app.core.schema import Schema
from app.domains.trainer import validation as trainer_validation

TrainerUsername = Annotated[str, pydantic.AfterValidator(trainer_validation.validate_username)]


class TrainerUsernameBody(Schema):
    username: TrainerUsername


class UsernameAvailabilityRead(Schema):
    available: bool
    detail: str | None = None
