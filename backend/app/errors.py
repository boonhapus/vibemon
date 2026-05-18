"""Vibemon error hierarchy.

All domain errors inherit from ``VibemonError`` so callers can catch a
single base when they need to.
"""

from __future__ import annotations


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


class PartyFull(VibemonServiceError):
    """Raised when adoption needs a release swap and none was supplied."""


class ReleaseUnavailable(VibemonServiceError):
    """Raised when a Vibemon cannot be released by the trainer."""
