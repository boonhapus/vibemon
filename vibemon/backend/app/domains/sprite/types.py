"""Shared sprite presentation vocabulary."""

import enum


class SpriteFacing(enum.StrEnum):
    """Horizontal orientation of a sprite in the image canvas."""

    LEFT = "LEFT"
    CENTER = "CENTER"
    RIGHT = "RIGHT"
