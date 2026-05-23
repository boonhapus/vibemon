"""Rehearse creating a Vibemon at a chosen UX stage."""

from __future__ import annotations

from typing import Annotated
import asyncio
import enum
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.core.time import resolve_clock
from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.workflows import _workflow_support as workflow_support
from app.workflows import candidate as candidate_workflow
from app.workflows import generate_wild_supply as wild_workflow
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

app = cyclopts.App(
    help=(
        "Create one Vibemon for local rehearsal.\n\n"
        "Start with a stage, then add only the story details you care about.\n"
        "Examples:\n"
        "  generate_vibemon.py\n"
        "  generate_vibemon.py manifested --nickname Mochi\n"
        "  generate_vibemon.py owned --trainer 0198... --name Ada --form manifested"
    )
)


class GenerationStage(enum.StrEnum):
    BORN = "born"
    CHRISTENED = "christened"
    MANIFESTED = "manifested"
    CANDIDATE = "candidate"
    WILD = "wild"
    OWNED = "owned"


@app.default
def generate_vibemon(
    *,
    stage: Annotated[
        GenerationStage,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Where in the UX flow this Vibemon should be created."),
    ] = GenerationStage.BORN,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID for candidate or owned stages."),
    ] = None,
    name: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer name to create when the trainer is new."),
    ] = None,
    nickname: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional Vibemon nickname."),
    ] = None,
    idea: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional creative identity seed."),
    ] = None,
    lifecycle: Annotated[
        VibemonLifecycleT | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Visual completeness for candidate, wild, or owned stages."),
    ] = None,
    location: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Birth location as 'latitude,longitude'; random if omitted."),
    ] = None,
    born_at: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Birth time as an ISO timestamp; now if omitted."),
    ] = None,
    database_url: Annotated[
        str,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Database URL for persisted script output."),
    ] = _common.default_database_url(),
    asset_store_url: Annotated[
        str,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, help="Blob/object store URL for generated assets."),
    ] = _common.DEFAULT_ASSET_STORE_URL,
    bypass_credits: Annotated[
        bool,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, negative="", help="Skip trainer generation credit checks."),
    ] = True,
) -> None:
    latitude, longitude = _resolve_location(location=location)

    asyncio.run(
        _run(
            stage=stage,
            trainer_id=trainer,
            username=name,
            latitude=latitude,
            longitude=longitude,
            timestamp=born_at,
            lifecycle=lifecycle or VibemonLifecycleT.BORN,
            database_url=database_url,
            asset_store_url=asset_store_url,
            nickname=nickname,
            core_identity=idea,
            bypass_credits=bypass_credits,
        )
    )


def _resolve_location(*, location: str | None) -> tuple[float, float]:
    if location is None:
        return _common.random_latitude(), _common.random_longitude()

    try:
        raw_latitude, raw_longitude = location.split(",", maxsplit=1)
        return float(raw_latitude.strip()), float(raw_longitude.strip())
    except ValueError as exc:
        raise SystemExit("--location must look like '37.7749,-122.4194'.") from exc


async def _run(
    *,
    stage: GenerationStage,
    trainer_id: uuid.UUID | None,
    username: str | None,
    latitude: float,
    longitude: float,
    timestamp: str | None,
    lifecycle: VibemonLifecycleT,
    database_url: str,
    asset_store_url: str,
    nickname: str | None,
    core_identity: str | None,
    bypass_credits: bool,
) -> None:
    os.environ["ASSET_STORE_URL"] = asset_store_url
    _common.ensure_local_blob_dir(asset_store_url)
    async with _common.session_scope(database_url=database_url) as sess:
        seed = _common.birth_seed(latitude=latitude, longitude=longitude, timestamp=timestamp)
        if stage in (GenerationStage.BORN, GenerationStage.CHRISTENED, GenerationStage.MANIFESTED):
            result = await _generate_plain_vibemon(
                sess,
                seed=seed,
                stage=stage,
                nickname=nickname,
                core_identity=core_identity,
            )
        elif stage is GenerationStage.WILD:
            result = await wild_workflow.generate_wild_supply(
                sess,
                birth_seed=seed,
                nickname=nickname,
                core_identity=core_identity,
                christen=lifecycle is not VibemonLifecycleT.BORN,
            )
            if lifecycle is VibemonLifecycleT.MANIFESTED:
                result = await _common.materialize_vibemon(sess, result.id, lifecycle=lifecycle)
        else:
            result = await _generate_trainer_stage(
                sess,
                seed=seed,
                stage=stage,
                trainer_id=trainer_id or uuid.uuid7(),
                username=username,
                lifecycle=lifecycle,
                nickname=nickname,
                core_identity=core_identity,
                bypass_credits=bypass_credits,
            )
    _common.dump({"stage": stage.value, "latitude": latitude, "longitude": longitude, "vibemon": result})


async def _generate_plain_vibemon(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    stage: GenerationStage,
    nickname: str | None,
    core_identity: str | None,
) -> PublicVibemon:
    row = await workflow_support.birth_and_persist_vibemon(
        sess,
        birth_seed=seed,
        nickname=nickname,
        core_identity=core_identity,
        now=resolve_clock(),
        christen=stage is not GenerationStage.BORN,
    )
    if stage is GenerationStage.MANIFESTED:
        return await _common.materialize_vibemon(sess, row.id, lifecycle=VibemonLifecycleT.MANIFESTED)
    await sess.flush()
    return await _common.load_public_vibemon(sess, row.id)


async def _generate_trainer_stage(
    sess: AsyncSession,
    *,
    seed: BirthSeed,
    stage: GenerationStage,
    trainer_id: uuid.UUID,
    username: str | None,
    lifecycle: VibemonLifecycleT,
    nickname: str | None,
    core_identity: str | None,
    bypass_credits: bool,
) -> PublicVibemon:
    await _common.ensure_trainer(sess, trainer_id, username=username)
    candidate = await candidate_workflow.generate_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        birth_seed=seed,
        nickname=nickname,
        core_identity=core_identity,
        bypass_credits=bypass_credits,
        christen=lifecycle is not VibemonLifecycleT.BORN,
    )
    if stage is GenerationStage.CANDIDATE:
        if lifecycle is VibemonLifecycleT.MANIFESTED:
            await _common.materialize_vibemon(sess, candidate.id, lifecycle=lifecycle)
        return await _common.load_public_vibemon(sess, candidate.id)
    return await candidate_workflow.adopt_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        vibemon_id=candidate.id,
        manifest=lifecycle is VibemonLifecycleT.MANIFESTED,
    )


if __name__ == "__main__":
    app()
