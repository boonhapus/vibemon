from __future__ import annotations

import structlog
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.plugins.attrs import AttrsSchemaPlugin

from app.logging import configure_logging
from app.middleware import RequestContextMiddleware

log = structlog.get_logger(__name__)


async def _log_startup() -> None:
    log.info("app_startup")


def create_app() -> Litestar:
    configure_logging()
    from litestar import Router

    from app.routes.generate import generate_endpoint
    from app.routes.health import health

    api_v1 = Router(path="/api/v1", route_handlers=[health, generate_endpoint])

    return Litestar(
        route_handlers=[api_v1],
        plugins=[AttrsSchemaPlugin()],
        cors_config=CORSConfig(
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        middleware=[RequestContextMiddleware()],
        on_startup=[_log_startup],
    )


app = create_app()
