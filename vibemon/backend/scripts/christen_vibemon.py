"""Christen a born Vibemon and persist generated assets."""

from __future__ import annotations

import asyncio
import uuid

import cyclopts

from app.storage.database import mapper, repositories
from app.workflows import _workflow_support as workflows
from app.workflows.materialize_vibemon import MaterializeVibemon
from scripts import _common

app = cyclopts.App(help="Christen a born Vibemon.")


@app.default
def christen_vibemon(
    *,
    vibemon_id: uuid.UUID,
    database_url: str = _common.default_database_url(),
    no_create_schema: bool = False,
) -> None:
    asyncio.run(_run(vibemon_id=vibemon_id, database_url=database_url, create_schema=not no_create_schema))


async def _run(*, vibemon_id: uuid.UUID, database_url: str, create_schema: bool) -> None:
    realizer = MaterializeVibemon()
    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        row = await repositories.load_vibemon(sess, vibemon_id)
        vibemon = await mapper.vibemon_from_row(row)
        vibemon = await realizer.christen(vibemon)
        mapper.apply_vibemon_to_row(row, vibemon)
        await repositories.persist_assets(sess, vibemon)
        await sess.flush()
        result = await workflows.public_vibemon(row)
    _common.dump(result)


if __name__ == "__main__":
    app()
