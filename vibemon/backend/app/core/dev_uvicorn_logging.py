"""Structlog-backed logging config for the uvicorn dev reloader."""

from typing import Any
import logging
import sys

import structlog


def dev_uvicorn_logging_config() -> dict[str, Any]:
    """Return a dictConfig for uvicorn that only surfaces errors via structlog."""
    structlog.configure(
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR),
        cache_logger_on_first_use=True,
    )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "foreign_pre_chain": [
                    structlog.stdlib.add_log_level,
                    structlog.processors.TimeStamper(fmt="%H:%M:%S", utc=False),
                ],
                "processors": [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()),
                ],
            },
        },
        "handlers": {
            "stderr": {
                "class": "logging.StreamHandler",
                "formatter": "structlog",
                "stream": "ext://sys.stderr",
                "level": "ERROR",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["stderr"], "level": "ERROR", "propagate": False},
            "uvicorn.error": {"handlers": ["stderr"], "level": "ERROR", "propagate": False},
            "uvicorn.access": {"handlers": [], "level": "ERROR", "propagate": False},
            "uvicorn.asgi": {"handlers": ["stderr"], "level": "ERROR", "propagate": False},
        },
    }
