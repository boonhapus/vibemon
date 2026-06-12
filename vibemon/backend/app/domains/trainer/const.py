"""Pinned trainer identifiers and catalog defaults."""

import uuid

CANONICAL_TRAINER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")
"""Reserved trainer row for the default style-bible reference shipped with the game."""

CANONICAL_TRAINER_USERNAME = "style-bible"
"""Username for :data:`CANONICAL_TRAINER_ID` — not used for player login."""
