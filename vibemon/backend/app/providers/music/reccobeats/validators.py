"""Reccobeats API response field validators and reusable annotated types."""

from typing import Annotated, Any

from pydantic import BeforeValidator


def translate_major_minor(value: Any) -> bool:
    if value is None:
        msg = "mode is required"
        raise ValueError(msg)
    if not isinstance(value, int):
        msg = "mode must be an integer"
        raise ValueError(msg)
    return value == 1


IsMajor = Annotated[bool, BeforeValidator(translate_major_minor)]
