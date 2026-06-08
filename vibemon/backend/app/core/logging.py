"""Structlog and Litestar logging configuration."""

from litestar.exceptions import NotAuthorizedException
from litestar.logging.config import LoggingConfig, StructLoggingConfig
from litestar.status_codes import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND


def litestar_logging_config() -> StructLoggingConfig:
    """Return Litestar logging config backed by structlog.

    Expected client errors (401/404) are excluded from exception tracebacks.
    Uvicorn access logs are disabled here; use structlog for request/error signal.
    """
    return StructLoggingConfig(
        log_exceptions="debug",
        disable_stack_trace={
            HTTP_401_UNAUTHORIZED,
            HTTP_404_NOT_FOUND,
            NotAuthorizedException,
        },
        standard_lib_logging_config=LoggingConfig(
            loggers={
                "uvicorn": {
                    "level": "INFO",
                    "handlers": ["queue_listener"],
                    "propagate": False,
                },
                "uvicorn.error": {
                    "level": "INFO",
                    "handlers": ["queue_listener"],
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "propagate": False,
                },
            },
        ),
    )
