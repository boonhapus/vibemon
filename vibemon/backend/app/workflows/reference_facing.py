"""Resolve which way a Vibemon's reference sprite faces for hatch UI reads."""

from app.domains.sprite import types as sprite_types
from app.domains.vibemon.entity import Vibemon


def resolve_reference_facing(vibemon: Vibemon) -> str:
    if vibemon.reference_detected_facing is not None:
        return vibemon.reference_detected_facing.value.lower()
    return sprite_types.SpriteFacing.LEFT.value.lower()
