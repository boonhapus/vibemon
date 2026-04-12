from __future__ import annotations

from typing import Any

import niquests
import structlog
from litestar import get

log = structlog.get_logger(__name__)

_OPEN_METEO = "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.12&current=temperature_2m"


@get("/health")
async def health() -> dict[str, Any]:
    providers: dict[str, str] = {"weather": "unknown"}
    try:
        async with niquests.AsyncSession() as session:
            r = await session.get(_OPEN_METEO, timeout=5)
        providers["weather"] = "ok" if r.status_code == 200 else f"error:{r.status_code}"
    except* Exception as eg:
        log.warning("health_open_meteo_failed", errors=[repr(e) for e in eg.exceptions])
        providers["weather"] = "unreachable"

    return {"status": "ok", "providers": providers}


__all__ = ["health"]
