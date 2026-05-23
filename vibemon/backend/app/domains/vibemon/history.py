"""Vibemon history event vocabulary."""

import enum


class VibemonHistoryEventT(enum.StrEnum):
    """Persisted lifecycle and gameplay history events."""

    CANDIDATE_SHOWN = "candidate_shown"
    CANDIDATE_ADOPTED = "candidate_adopted"
    CANDIDATE_REJECTED = "candidate_rejected"
    CANDIDATE_TIMED_OUT = "candidate_timed_out"
    RELEASED = "released"
    WILD_ENCOUNTER_STARTED = "wild_encounter_started"
    WILD_ENCOUNTER_COMPLETED = "wild_encounter_completed"
    EXPIRED = "expired"
