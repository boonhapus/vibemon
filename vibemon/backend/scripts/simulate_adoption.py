"""Rehearse trainer candidate review and adoption behavior."""

from typing import Annotated
import asyncio
import enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.domains.generation.seed import BirthSeed
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.types import VibemonLifecycleT
from app.storage.database import mapper, vibemon_repo
from app.workflows import public_projection
from app.workflows.materialize_vibemon import MaterializeVibemon
from app.workflows import birth_seed as birth_seed_factory
from app.workflows import candidate as candidate_workflow
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

app = cyclopts.App(
    help=(
        "Rehearse trainer review of a candidate Vibemon.\n\n"
        "Create a candidate, then either adopt or reject it with optional trainer and seed details.\n"
        "Examples:\n"
        "  simulate_adoption.py\n"
        "  simulate_adoption.py --action reject --nickname Mochi\n"
        "  simulate_adoption.py --trainer 0198... --name Ada --release 0198... --lifecycle manifested"
    )
)


class AdoptionAction(enum.StrEnum):
    ADOPT = "adopt"
    REJECT = "reject"


@app.default
def simulate_adoption(
    *,
    action: Annotated[
        AdoptionAction,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="How the trainer resolves the generated candidate."),
    ] = AdoptionAction.ADOPT,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID; random if omitted."),
    ] = None,
    name: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer name to create when the trainer is new."),
    ] = None,
    release: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Owned Vibemon UUID to release if adoption needs room."),
    ] = None,
    lifecycle: Annotated[
        VibemonLifecycleT,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Visual completeness for the generated candidate."),
    ] = VibemonLifecycleT.BORN,
    location: Annotated[
        str | None,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            help="Candidate birth location as 'latitude,longitude'; random if omitted.",
        ),
    ] = None,
    born_at: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Candidate birth time as an ISO timestamp; now if omitted."),
    ] = None,
    nickname: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Optional candidate nickname."),
    ] = None,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
    asset_store_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Asset store URL override; defaults to VIBEMON_STORAGE__ASSETS.",
        ),
    ] = None,
    bypass_credits: Annotated[
        bool,
        cyclopts.Parameter(group=ADVANCED_OPTIONS, negative="", help="Skip trainer generation credit checks."),
    ] = True,
) -> None:
    storage = _common.load_script_settings(database_url=database_url, asset_store_url=asset_store_url)
    latitude, longitude = _resolve_location(location=location)

    asyncio.run(
        _run(
            action=action,
            trainer_id=trainer or uuid.uuid7(),
            username=name,
            release_vibemon_id=release,
            latitude=latitude,
            longitude=longitude,
            timestamp=born_at,
            candidate_lifecycle=lifecycle,
            database_url=storage.storage.database,
            asset_store_url=storage.storage.assets,
            nickname=nickname,
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
    action: AdoptionAction,
    trainer_id: uuid.UUID,
    username: str | None,
    release_vibemon_id: uuid.UUID | None,
    latitude: float,
    longitude: float,
    timestamp: str | None,
    candidate_lifecycle: VibemonLifecycleT,
    database_url: str,
    asset_store_url: str,
    nickname: str | None,
    bypass_credits: bool,
) -> None:
    _common.ensure_local_blob_dir(asset_store_url)
    async with _common.session_scope(database_url=database_url) as sess:
        seed = birth_seed_factory.build_birth_seed(
            trainer_id=_common.SCRIPT_ANONYMOUS_TRAINER_ID,
            latitude=latitude,
            longitude=longitude,
            timestamp=_common.parse_datetime(timestamp) if timestamp is not None else None,
        )
        result = await _simulate(
            sess,
            action=action,
            trainer_id=trainer_id,
            username=username,
            release_vibemon_id=release_vibemon_id,
            seed=seed,
            candidate_lifecycle=candidate_lifecycle,
            nickname=nickname,
            bypass_credits=bypass_credits,
        )
    _common.dump(result)


async def _materialize_vibemon(
    sess: AsyncSession,
    vibemon_id: uuid.UUID,
    *,
    lifecycle: VibemonLifecycleT,
) -> PublicVibemon:
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    if lifecycle is VibemonLifecycleT.CHRISTENED:
        vibemon = await MaterializeVibemon().christen(vibemon)
    elif lifecycle is VibemonLifecycleT.MANIFESTED:
        vibemon = await MaterializeVibemon().christen_and_manifest(vibemon)
    mapper.apply_vibemon_to_row(row, vibemon)
    await vibemon_repo.persist_assets(sess, vibemon)
    await sess.flush()
    return await public_projection.public_vibemon(row)


async def _simulate(
    sess: AsyncSession,
    *,
    action: AdoptionAction,
    trainer_id: uuid.UUID,
    username: str | None,
    release_vibemon_id: uuid.UUID | None,
    seed: BirthSeed,
    candidate_lifecycle: VibemonLifecycleT,
    nickname: str | None,
    bypass_credits: bool,
) -> dict[str, object]:
    await _common.ensure_trainer(sess, trainer_id, username=username)
    candidate = await candidate_workflow.generate_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        birth_seed=seed,
        nickname=nickname,
        bypass_credits=bypass_credits,
        christen=candidate_lifecycle is not VibemonLifecycleT.BORN,
    )
    if action is AdoptionAction.REJECT and candidate_lifecycle is VibemonLifecycleT.MANIFESTED:
        candidate = await _materialize_vibemon(sess, candidate.id, lifecycle=candidate_lifecycle)

    if action is AdoptionAction.REJECT:
        resolved = await candidate_workflow.reject_candidate(
            sess,
            trainer_id=_common.trainer_id(trainer_id),
            vibemon_id=candidate.id,
        )
    else:
        resolved = await candidate_workflow.adopt_candidate(
            sess,
            trainer_id=_common.trainer_id(trainer_id),
            vibemon_id=candidate.id,
            release_vibemon_id=release_vibemon_id,
            manifest=candidate_lifecycle is VibemonLifecycleT.MANIFESTED,
        )

    return {
        "experience": "adoption",
        "trainer_id": str(trainer_id),
        "action": action.value,
        "candidate": candidate,
        "result": resolved,
    }


if __name__ == "__main__":
    app()
