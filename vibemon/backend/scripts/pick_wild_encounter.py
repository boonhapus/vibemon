"""CLI adapter for the pick-wild-encounter workflow."""

from __future__ import annotations

import asyncio
import uuid

import cyclopts

from app.workflows import wild_encounter as workflow
from scripts import _common

app = cyclopts.App(help="Pick an eligible wild Vibemon encounter.")


@app.default
def pick_wild_encounter(
    *,
    trainer_id: uuid.UUID,
    latitude: float,
    longitude: float,
    party_strength: float,
    database_url: str = _common.default_database_url(),
    no_create_schema: bool = False,
    desired_supply: int = 12,
) -> None:
    asyncio.run(
        _run(
            trainer_id=trainer_id,
            latitude=latitude,
            longitude=longitude,
            party_strength=party_strength,
            database_url=database_url,
            create_schema=not no_create_schema,
            desired_supply=desired_supply,
        )
    )


async def _run(
    *,
    trainer_id: uuid.UUID,
    latitude: float,
    longitude: float,
    party_strength: float,
    database_url: str,
    create_schema: bool,
    desired_supply: int,
) -> None:
    async with _common.session_scope(database_url=database_url, create_schema=create_schema) as sess:
        result = await workflow.pick_wild_encounter(
            sess,
            trainer_id=_common.trainer_id(trainer_id),
            latitude=latitude,
            longitude=longitude,
            party_strength=party_strength,
            desired_supply=desired_supply,
        )
    _common.dump(result)


if __name__ == "__main__":
    app()
