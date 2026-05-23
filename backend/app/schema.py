"""Compatibility re-export shim for domain schemas.

Prefer importing from `app.domain.*` for new code.
"""

from app.domain.birth import BirthSeed, BirthSnapshot, FrozenSchema, Schema
from app.domain.move import (
    Condition,
    ConditionalOverride,
    Drain,
    Effect,
    EffectGroup,
    EffectTarget,
    Heal,
    IfHpBelow,
    IfOpponentAttacking,
    IfWeather,
    Move,
    MoveBehavior,
    RandomPower,
    Recoil,
    StatChange,
    StatusInflict,
    WeatherSet,
    canonicalize_move_name,
    validate_move_id,
)
from app.domain.read_models import (
    CandidateReviewRead,
    PublicAsset,
    PublicVibemon,
    TypeCoverageSummary,
    TypeDefenseSummary,
    TypeMatchupSummary,
)
from app.domain.vibemon import Aesthetic, Affinity, BirthOutcome, Identity, Trainer, Vibemon

__all__ = [
    "Aesthetic",
    "Affinity",
    "BirthOutcome",
    "BirthSeed",
    "BirthSnapshot",
    "CandidateReviewRead",
    "Condition",
    "ConditionalOverride",
    "Drain",
    "Effect",
    "EffectGroup",
    "EffectTarget",
    "FrozenSchema",
    "Heal",
    "Identity",
    "IfHpBelow",
    "IfOpponentAttacking",
    "IfWeather",
    "Move",
    "MoveBehavior",
    "PublicAsset",
    "PublicVibemon",
    "RandomPower",
    "Recoil",
    "Schema",
    "StatChange",
    "StatusInflict",
    "Trainer",
    "TypeCoverageSummary",
    "TypeDefenseSummary",
    "TypeMatchupSummary",
    "Vibemon",
    "WeatherSet",
    "canonicalize_move_name",
    "validate_move_id",
]
