"""Wild encounter vocabularies."""

import enum


class WildEncounterOutcomeT(enum.StrEnum):
    """Outcomes that apply trainer-specific encounter adjustments."""

    RUN = "run"
    DEFEAT = "defeat"
    WIN_NO_ADOPT = "win_no_adopt"
