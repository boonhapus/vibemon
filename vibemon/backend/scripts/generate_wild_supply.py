"""CLI adapter for the generate-wild-supply workflow."""

from __future__ import annotations

from typing import Annotated
import asyncio

import cyclopts

from app.workflows import generate_wild_supply as workflow
from scripts import _common

app = cyclopts.App(help="Generate a wild Vibemon.")


@app.default
def generate_wild_supply(
    *,
    latitude: float,
    longitude: float,
    timestamp: Annotated[str | None, cyclopts.Parameter(help="ISO timestamp; UTC if omitted.")] = None,
    database_url: str = _common.default_database_url(),
    no_create_schema: bool = False,
    nickname: str | None = None,
    core_identity: str | None = None,
    christen: bool = False,
) -> None:
    asyncio.run(
        _run(
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            database_url=database_url,
            create_schema=not no_create_schema,
            nickname=nickname,
            core_identity=core_identity,
            christen=christen,
        )
    )


async def _run(
    *,
    latitude: float,
    longitude: float,
    timestamp: str | None,
    database_url: str,
    create_schema: bool,
    nickname: str | None,
    core_identity: str | None,
    christen: bool,
) -> None:
    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        result = await workflow.generate_wild_supply(
            sess,
            birth_seed=_common.birth_seed(latitude=latitude, longitude=longitude, timestamp=timestamp),
            nickname=nickname,
            core_identity=core_identity,
            christen=christen,
        )
    _common.dump(result)


if __name__ == "__main__":
    app()
