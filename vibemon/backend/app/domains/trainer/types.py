"""Trainer domain vocabulary."""

from typing import Literal

type TrainerSecretKindT = Literal["lastfm.session_key", "lastfm.username"]
"""Allowed ``trainer_secret.kind`` values stored encrypted at rest."""

LASTFM_SESSION_KEY: TrainerSecretKindT = "lastfm.session_key"
LASTFM_USERNAME: TrainerSecretKindT = "lastfm.username"
