"""Health check route."""

from litestar import Router, get


@get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


health_router = Router(path="/api", route_handlers=[healthz])
