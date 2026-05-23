"""Adoption workflow vocabularies."""

import enum


class CandidateReviewStatusT(enum.StrEnum):
    """Resolution state for a candidate review."""

    PENDING = "pending"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
