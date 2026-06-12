"""Run uvicorn for dev_stack with quiet structlog-backed reload logging."""

import argparse
import pathlib

import uvicorn

from app.core.dev_uvicorn_logging import dev_uvicorn_logging_config

BACKEND = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(
        "app.http.app:app",
        host=args.host,
        port=args.port,
        reload=True,
        reload_dirs=[str(BACKEND / "app")],
        access_log=False,
        log_config=dev_uvicorn_logging_config(),
        log_level="error",
    )


if __name__ == "__main__":
    main()
