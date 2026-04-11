from __future__ import annotations

from typing import Any, cast

import structlog
from litestar import Request, post
from litestar.exceptions import HTTPException
from litestar.status_codes import HTTP_200_OK, HTTP_422_UNPROCESSABLE_ENTITY

from app.engine.orchestrator import generate_from_dict

log = structlog.get_logger(__name__)


@post("/generate", status_code=HTTP_200_OK)
async def generate_endpoint(request: Request) -> dict[str, Any]:
    data = cast(dict[str, Any], await request.json())
    if data.get("latitude") is None or data.get("longitude") is None:
        raise HTTPException(
            detail="latitude and longitude are required",
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        )
    try:
        lat = float(data["latitude"])
        lon = float(data["longitude"])
    except (TypeError, ValueError) as err:
        raise HTTPException(
            detail="latitude and longitude must be numbers",
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        ) from err

    payload = {**data, "latitude": lat, "longitude": lon}
    if not payload.get("user_id"):
        raise HTTPException(
            detail="user_id is required",
            status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        )

    try:
        return await generate_from_dict(payload)
    except Exception:
        log.exception("generate_failed")
        raise


__all__ = ["generate_endpoint"]
