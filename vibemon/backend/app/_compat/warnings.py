"""Suppress known third-party warnings we cannot fix upstream."""

import warnings

_PYDANTIC_V1_ON_314 = r"Core Pydantic V1 functionality isn't compatible with Python 3\.14 or greater\."


def suppress_third_party_warnings() -> None:
    """Hide dependency noise that is not actionable in this repo."""
    for module in (
        "litestar.plugins.pydantic.utils",
        "elevenlabs.core.pydantic_utilities",
    ):
        warnings.filterwarnings(
            "ignore",
            message=_PYDANTIC_V1_ON_314,
            category=UserWarning,
            module=module,
        )
