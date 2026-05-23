"""CLI adapter for the adopt-candidate workflow."""

from __future__ import annotations

import asyncio
import uuid

import cyclopts

from app.workflows import candidate as workflow
from scripts import _common

app = cyclopts.App(help="Adopt a pending candidate Vibemon.")


@app.default
def adopt_candidate(
    *,
    trainer_id: uuid.UUID,
    vibemon_id: uuid.UUID,
    database_url: str = _common.default_database_url(),
    no_create_schema: bool = False,
    release_vibemon_id: uuid.UUID | None = None,
    manifest: bool = False,
) -> None:
    asyncio.run(
        _run(
            trainer_id=trainer_id,
            vibemon_id=vibemon_id,
            database_url=database_url,
            create_schema=not no_create_schema,
            release_vibemon_id=release_vibemon_id,
            manifest=manifest,
        )
    )


async def _run(
    *,
    trainer_id: uuid.UUID,
    vibemon_id: uuid.UUID,
    database_url: str,
    create_schema: bool,
    release_vibemon_id: uuid.UUID | None,
    manifest: bool,
) -> None:
    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        result = await workflow.adopt_candidate(
            sess,
            trainer_id=_common.trainer_id(trainer_id),
            vibemon_id=vibemon_id,
            release_vibemon_id=release_vibemon_id,
            manifest=manifest,
        )
    _common.dump(result)


if __name__ == "__main__":
    app()
