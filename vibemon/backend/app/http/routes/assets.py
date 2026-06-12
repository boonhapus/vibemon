"""Serve binary blobs from the configured asset store."""

from litestar import Router, get
from litestar.exceptions import NotFoundException
from litestar.response import Response

from app.storage.blob import const as blob_const
from app.storage.blob.monstore import get_default_monstore


@get("/{key:path}")
async def get_asset(key: str) -> Response[bytes]:
    """Stream one object from monstore by key."""
    monstore = get_default_monstore()
    try:
        data = await monstore.get(key)
    except FileNotFoundError as exc:
        raise NotFoundException(detail="Asset not found.") from exc

    content_type = blob_const.CONTENT_TYPE_BY_EXTENSION.get(key.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    return Response(content=data, media_type=content_type)


assets_router = Router(path="/api/assets", route_handlers=[get_asset])
