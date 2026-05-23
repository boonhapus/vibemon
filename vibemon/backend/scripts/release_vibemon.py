"""CLI adapter for the release-Vibemon workflow."""

from __future__ import annotations

import asyncio
import uuid

import cyclopts

from app.workflows import release_vibemon as workflow
from scripts import _common

app = cyclopts.App(help="Release an owned Vibemon back to the wild.")


@app.default
def release_vibemon(
    *,
    trainer_id: uuid.UUID,
    vibemon_id: uuid.UUID,
    database_url: str = _common.default_database_url(),
    no_create_schema: bool = False,
) -> None:
    asyncio.run(
        _run(
            trainer_id=trainer_id,
            vibemon_id=vibemon_id,
            database_url=database_url,
            create_schema=not no_create_schema,
        )
    )


async def _run(
    *,
    trainer_id: uuid.UUID,
    vibemon_id: uuid.UUID,
    database_url: str,
    create_schema: bool,
) -> None:
    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        result = await workflow.release_vibemon(
            sess,
            trainer_id=_common.trainer_id(trainer_id),
            vibemon_id=vibemon_id,
        )
    _common.dump(result)


if __name__ == "__main__":
    app()
