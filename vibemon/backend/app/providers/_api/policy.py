import niquests

from app import __project__


def provider_default_headers(*, accept: str = "application/json") -> dict[str, str]:
    """Default HTTP headers for outbound provider API clients."""
    return {
        "accept": accept,
        "user-agent": f"{__project__.__name__} v{__project__.__version__} (+github/{__project__.__slug__})",
    }


def provider_retry_policy(*, total: int = 5) -> niquests.RetryConfiguration:
    """
    Retry transient HTTP failures with exponential backoff.

    Shared by provider API clients. With ``backoff_factor=2``, waits are roughly
    2s, 4s, 8s, … between attempts (plus any ``Retry-After`` header from the server).
    """
    return niquests.RetryConfiguration(
        total=total,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503],
        allowed_methods=["GET"],
        raise_on_status=False,
        respect_retry_after_header=True,
    )
