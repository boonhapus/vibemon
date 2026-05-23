"""Cyclopts CLI: spawn a wild Vibemon via the canonical wild-supply flow."""

from __future__ import annotations

from typing import Annotated
import asyncio
import os
import random

import cyclopts

from scripts import _common

app = cyclopts.App(help="Spawn a wild Vibemon by running the wild-supply workflow.")


@app.default
def spawn(
    *,
    database_url: Annotated[str, cyclopts.Parameter(help="Async SQLAlchemy URL.")] = _common.default_database_url(),
    asset_store_url: Annotated[
        str, cyclopts.Parameter(help="obstore URL for blob assets.")
    ] = _common.DEFAULT_ASSET_STORE_URL,
    latitude: Annotated[float | None, cyclopts.Parameter(help="Birth latitude; random if omitted.")] = None,
    longitude: Annotated[float | None, cyclopts.Parameter(help="Birth longitude; random if omitted.")] = None,
    nickname: str | None = None,
    core_identity: str | None = None,
    christen: Annotated[bool, cyclopts.Parameter(help="Run christen step (name + reference + cry).")] = True,
    no_create_schema: bool = False,
) -> None:
    if latitude is None:
        latitude = random.uniform(-90.0, 90.0)
    if longitude is None:
        longitude = random.uniform(-180.0, 180.0)

    os.environ["ASSET_STORE_URL"] = asset_store_url
    _common.ensure_local_blob_dir(asset_store_url)

    asyncio.run(
        _run(
            database_url=database_url,
            latitude=latitude,
            longitude=longitude,
            nickname=nickname,
            core_identity=core_identity,
            christen=christen,
            create_schema=not no_create_schema,
        )
    )


async def _run(
    *,
    database_url: str,
    latitude: float,
    longitude: float,
    nickname: str | None,
    core_identity: str | None,
    christen: bool,
    create_schema: bool,
) -> None:
    from app.workflows import generate_wild_supply as workflow

    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        result = await workflow.generate_wild_supply(
            sess,
            birth_seed=_common.birth_seed(latitude=latitude, longitude=longitude),
            nickname=nickname,
            core_identity=core_identity,
            christen=christen,
        )
    _common.dump(result)


if __name__ == "__main__":
    app()
