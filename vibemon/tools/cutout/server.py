"""Start the local bbox cutout web UI."""

from http.server import ThreadingHTTPServer
from typing import Annotated

import cyclopts
import structlog

from core import configure_logging
from web import CutoutHandler
from paths import REPO_ROOT, STATIC_DIR

_LOGGER = structlog.get_logger(__name__)

app = cyclopts.App(help="Start the local bbox cutout web UI.")


@app.default
def main(
    *,
    host: Annotated[str, cyclopts.Parameter(help="Bind host.")] = "127.0.0.1",
    port: Annotated[int, cyclopts.Parameter(help="Bind port.")] = 8765,
    verbose: Annotated[bool, cyclopts.Parameter(help="Enable debug logging.")] = False,
) -> None:
    """Serve the interactive cutout UI."""
    configure_logging(verbose=verbose)
    if not STATIC_DIR.is_dir():
        raise SystemExit(f"Missing static directory: {STATIC_DIR}")

    server = ThreadingHTTPServer((host, port), CutoutHandler)
    url = f"http://{host}:{port}"
    _LOGGER.info(
        "cutout_ui_started",
        url=url,
        host=host,
        port=port,
        repo_root=str(REPO_ROOT),
        static_dir=str(STATIC_DIR),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _LOGGER.info("cutout_ui_stopped", url=url)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
