"""Shared identifier types."""

from typing import Annotated
import uuid

type TrainerIdT = Annotated[uuid.UUID, "backend trainer identifier"]
