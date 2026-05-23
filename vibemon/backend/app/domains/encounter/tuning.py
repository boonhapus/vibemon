"""Centralized tuning constants for wild encounter matching and weighting."""

from __future__ import annotations

import datetime as dt
import random

WILD_TARGET_RATIO = 0.45
WILD_STRENGTH_BAND_MIN = 0.70
WILD_STRENGTH_BAND_MAX = 1.40

ADJUSTMENT_MULTIPLIER_REJECTED = 0.00
ADJUSTMENT_MULTIPLIER_TIMED_OUT = 0.00
ADJUSTMENT_MULTIPLIER_RUN = 0.30
ADJUSTMENT_MULTIPLIER_DEFEAT = 0.50
ADJUSTMENT_MULTIPLIER_WIN_NO_ADOPT = 0.75

# Keyed by the string values of CandidateReviewStatusT and WildEncounterOutcomeT.
ADJUSTMENT_MULTIPLIER_BY_SOURCE: dict[str, float] = {
    "rejected": ADJUSTMENT_MULTIPLIER_REJECTED,
    "timed_out": ADJUSTMENT_MULTIPLIER_TIMED_OUT,
    "run": ADJUSTMENT_MULTIPLIER_RUN,
    "defeat": ADJUSTMENT_MULTIPLIER_DEFEAT,
    "win_no_adopt": ADJUSTMENT_MULTIPLIER_WIN_NO_ADOPT,
}

ADJUSTMENT_COOLDOWN_MIN = dt.timedelta(days=1)
ADJUSTMENT_COOLDOWN_MAX = dt.timedelta(days=3)

WILD_EXPIRATION_WINDOW = dt.timedelta(days=30)


def cooldown_duration(rng: random.Random) -> dt.timedelta:
    span = ADJUSTMENT_COOLDOWN_MAX - ADJUSTMENT_COOLDOWN_MIN
    random_seconds = rng.random() * span.total_seconds()
    return ADJUSTMENT_COOLDOWN_MIN + dt.timedelta(seconds=random_seconds)
