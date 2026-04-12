from __future__ import annotations

import structlog
from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send

from app.logging import new_request_id


class RequestContextMiddleware(ASGIMiddleware):
    scopes = (ScopeType.HTTP,)

    async def handle(
        self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp
    ) -> None:
        rid = new_request_id()
        structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            await next_app(scope, receive, send)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
