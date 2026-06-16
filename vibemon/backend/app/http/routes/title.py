"""Public title-screen routes."""

from typing import Annotated

from litestar import Router, get
from litestar.params import Parameter
from sqlalchemy.ext.asyncio import AsyncSession
import sqlalchemy as sa

from app.domains.vibemon import assets as vibemon_assets
from app.http.schemas import title as title_schemas
from app.storage.blob.monstore import get_default_monstore
from app.storage.database import models

_MAX_TITLE_MONS = 4


@get("/mons")
async def list_title_mons(
    db: AsyncSession,
    count: Annotated[int, Parameter(query="count", ge=1, le=_MAX_TITLE_MONS)] = _MAX_TITLE_MONS,
) -> title_schemas.TitleMonListRead:
    """Return random Vibemon reference sprites for the title-screen grass silhouettes."""
    rows = (
        await db.execute(
            sa.select(models.VibemonAsset)
            .where(models.VibemonAsset.kind == vibemon_assets.AssetKind.REFERENCE.value)
            .order_by(sa.func.random())
            .limit(count)
        )
    ).scalars()

    monstore = get_default_monstore()
    mons = tuple(
        title_schemas.TitleMonRead(
            id=asset.vibemon_id,
            reference_url=monstore.http_asset_url(asset.object_key),
        )
        for asset in rows
    )
    return title_schemas.TitleMonListRead(mons=mons)


title_router = Router(path="/api/title", route_handlers=[list_title_mons])
