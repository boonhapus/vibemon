import pytest

from app import errors


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (
            errors.GenerationCreditUnavailable("no credit"),
            errors.InterfaceErrorCode.GENERATION_CREDIT_UNAVAILABLE,
        ),
        (
            errors.GenerationAlreadyActive("active"),
            errors.InterfaceErrorCode.GENERATION_ALREADY_ACTIVE,
        ),
        (
            errors.CandidateReviewUnavailable("gone"),
            errors.InterfaceErrorCode.CANDIDATE_REVIEW_UNAVAILABLE,
        ),
        (
            errors.PartyFull("full"),
            errors.InterfaceErrorCode.PARTY_FULL,
        ),
        (
            errors.ReleaseUnavailable("not owned"),
            errors.InterfaceErrorCode.RELEASE_UNAVAILABLE,
        ),
    ],
)
def test_service_errors_map_to_stable_interface_codes(
    error: errors.VibemonServiceError,
    code: errors.InterfaceErrorCode,
) -> None:
    assert errors.interface_error_code(error) == code


def test_unknown_errors_map_to_internal_error() -> None:
    assert errors.interface_error_code(RuntimeError("boom")) == errors.InterfaceErrorCode.INTERNAL_ERROR
