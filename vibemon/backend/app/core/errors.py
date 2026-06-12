"""Vibemon error hierarchy.

All domain errors inherit from ``VibemonError`` so callers can catch a
single base when they need to.
"""

import enum


class VibemonError(RuntimeError):
    """Base error for all Vibemon domain failures."""


class VibemonServiceError(VibemonError):
    """Base error for Vibemon service-layer failures."""


class GenerationCreditUnavailable(VibemonServiceError):
    """Raised when a trainer has no usable generation credit."""


class GenerationAlreadyActive(VibemonServiceError):
    """Raised when a trainer already has a generation hold."""


class CandidateReviewUnavailable(VibemonServiceError):
    """Raised when a pending candidate review cannot be acted on."""


class CrewFull(VibemonServiceError):
    """Raised when adoption needs a release swap and none was supplied."""


class ReleaseUnavailable(VibemonServiceError):
    """Raised when a Vibemon cannot be released by the trainer."""


class WildEncounterUnavailable(VibemonServiceError):
    """Raised when no Wild encounter can be started."""


class BattleUnavailable(VibemonServiceError):
    """Raised when a battle cannot be started or continued."""


class MusicListeningUnavailable(VibemonError):
    """Raised when music birth preconditions fail (empty history or ReccoBeats fetch failure)."""


class MusicLinkRequired(VibemonServiceError):
    """Raised when music is opted in but the trainer has no linked Last.fm account."""


class ProviderNotImplemented(VibemonServiceError):
    """Raised when fetch is requested for a catalog provider without a backend implementation."""


class ProviderConfigRequired(VibemonServiceError):
    """Raised when a provider is enabled but its configuration requirements are not met."""


class InterfaceErrorCode(enum.StrEnum):
    """Stable API-facing error codes for typed service failures."""

    GENERATION_CREDIT_UNAVAILABLE = "generation_credit_unavailable"
    GENERATION_ALREADY_ACTIVE = "generation_already_active"
    CANDIDATE_REVIEW_UNAVAILABLE = "candidate_review_unavailable"
    CREW_FULL = "crew_full"
    RELEASE_UNAVAILABLE = "release_unavailable"
    WILD_ENCOUNTER_UNAVAILABLE = "wild_encounter_unavailable"
    BATTLE_UNAVAILABLE = "battle_unavailable"
    MUSIC_LINK_REQUIRED = "music_link_required"
    PROVIDER_NOT_IMPLEMENTED = "provider_not_implemented"
    PROVIDER_CONFIG_REQUIRED = "provider_config_required"
    INTERNAL_ERROR = "internal_error"


_SERVICE_ERROR_CODES: dict[type[VibemonServiceError], InterfaceErrorCode] = {
    GenerationCreditUnavailable: InterfaceErrorCode.GENERATION_CREDIT_UNAVAILABLE,
    GenerationAlreadyActive: InterfaceErrorCode.GENERATION_ALREADY_ACTIVE,
    CandidateReviewUnavailable: InterfaceErrorCode.CANDIDATE_REVIEW_UNAVAILABLE,
    CrewFull: InterfaceErrorCode.CREW_FULL,
    ReleaseUnavailable: InterfaceErrorCode.RELEASE_UNAVAILABLE,
    WildEncounterUnavailable: InterfaceErrorCode.WILD_ENCOUNTER_UNAVAILABLE,
    BattleUnavailable: InterfaceErrorCode.BATTLE_UNAVAILABLE,
    MusicLinkRequired: InterfaceErrorCode.MUSIC_LINK_REQUIRED,
    ProviderNotImplemented: InterfaceErrorCode.PROVIDER_NOT_IMPLEMENTED,
    ProviderConfigRequired: InterfaceErrorCode.PROVIDER_CONFIG_REQUIRED,
}


def interface_error_code(error: Exception) -> InterfaceErrorCode:
    """Map a typed domain/service exception to a stable interface error code."""

    if not isinstance(error, VibemonServiceError):
        return InterfaceErrorCode.INTERNAL_ERROR
    for error_type, code in _SERVICE_ERROR_CODES.items():
        if isinstance(error, error_type):
            return code
    return InterfaceErrorCode.INTERNAL_ERROR
