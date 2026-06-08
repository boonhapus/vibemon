"""Rehearse searching the wild, battling an encounter, and recording outcome."""

from typing import Annotated
import asyncio
import enum
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import cyclopts

from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.vibemon.strength import member_strength
from app.workflows import candidate as candidate_workflow
from app.workflows import generate_wild_supply as wild_supply_workflow
from app.workflows import wild_encounter as wild_encounter_workflow
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)

app = cyclopts.App(
    help=(
        "Rehearse a trainer searching the wild and resolving an encounter.\n\n"
        "Create any missing trainer or hero context, generate wild supply, then record the chosen outcome.\n"
        "Examples:\n"
        "  simulate_wild_encounter.py\n"
        "  simulate_wild_encounter.py --resolution run --location 37.7749,-122.4194\n"
        "  simulate_wild_encounter.py --hero 0198... --generate 6 --seed 42"
    )
)


class EncounterResolution(enum.StrEnum):
    AUTO_BATTLE = "auto_battle"
    RUN = "run"
    DEFEAT = "defeat"
    WIN_NO_ADOPT = "win_no_adopt"


@app.default
def simulate_wild_encounter(
    *,
    resolution: Annotated[
        EncounterResolution,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="How the selected wild encounter should resolve."),
    ] = EncounterResolution.AUTO_BATTLE,
    trainer: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID; random if omitted."),
    ] = None,
    name: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer name to create when the trainer is new."),
    ] = None,
    hero: Annotated[
        uuid.UUID | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Owned Vibemon UUID to battle with; generated if omitted."),
    ] = None,
    location: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Search location as 'latitude,longitude'; random if omitted."),
    ] = None,
    searched_at: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Search time as an ISO timestamp; now if omitted."),
    ] = None,
    generate: Annotated[
        int,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Number of wild Vibemon to generate before selecting."),
    ] = 3,
    supply: Annotated[
        int,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Desired nearby wild supply before selection."),
    ] = 12,
    seed: Annotated[
        int | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Random seed for deterministic battle rolls."),
    ] = 1,
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
) -> None:
    storage = _common.load_script_settings(database_url=database_url, asset_store_url=asset_store_url)
    latitude, longitude = _resolve_location(location=location)

    asyncio.run(
        _run(
            trainer_id=trainer or uuid.uuid7(),
            username=name,
            hero_vibemon_id=hero,
            latitude=latitude,
            longitude=longitude,
            timestamp=searched_at,
            wild_to_generate=generate,
            desired_supply=supply,
            resolution=resolution,
            database_url=storage.storage.database,
            asset_store_url=storage.storage.assets,
            rng_seed=seed,
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
    trainer_id: uuid.UUID,
    username: str | None,
    hero_vibemon_id: uuid.UUID | None,
    latitude: float,
    longitude: float,
    timestamp: str | None,
    wild_to_generate: int,
    desired_supply: int,
    resolution: EncounterResolution,
    database_url: str,
    asset_store_url: str,
    rng_seed: int | None,
) -> None:
    _common.ensure_local_blob_dir(asset_store_url)
    async with _common.session_scope(database_url=database_url) as sess:
        result = await _simulate(
            sess,
            trainer_id=trainer_id,
            username=username,
            hero_vibemon_id=hero_vibemon_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
            wild_to_generate=wild_to_generate,
            desired_supply=desired_supply,
            resolution=resolution,
            rng_seed=rng_seed,
        )
    _common.dump(result)


async def _simulate(
    sess: AsyncSession,
    *,
    trainer_id: uuid.UUID,
    username: str | None,
    hero_vibemon_id: uuid.UUID | None,
    latitude: float,
    longitude: float,
    timestamp: str | None,
    wild_to_generate: int,
    desired_supply: int,
    resolution: EncounterResolution,
    rng_seed: int | None,
) -> dict[str, object]:
    await _common.ensure_trainer(sess, trainer_id, username=username)
    if hero_vibemon_id is None:
        hero_vibemon_id = await _generate_owned_hero(
            sess,
            trainer_id=trainer_id,
            latitude=latitude,
            longitude=longitude,
            timestamp=timestamp,
        )

    generated_wild = []
    for _ in range(max(wild_to_generate, 0)):
        generated = await wild_supply_workflow.generate_wild_supply(
            sess,
            birth_seed=_common.birth_seed(latitude=latitude, longitude=longitude, timestamp=timestamp),
        )
        generated_wild.append(generated.id)

    hero_row = await _load_strength_row(sess, hero_vibemon_id)
    selection = await wild_encounter_workflow.pick_wild_encounter(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        latitude=latitude,
        longitude=longitude,
        crew_strength=member_strength(hero_row),  # pyrefly: ignore
        desired_supply=desired_supply,
    )
    if selection is None:
        return {
            "experience": "wild_encounter",
            "trainer_id": str(trainer_id),
            "hero_vibemon_id": str(hero_vibemon_id),
            "generated_wild_ids": [str(id_) for id_ in generated_wild],
            "selection": None,
        }

    battle = None
    outcome = _manual_outcome(resolution)
    if resolution is EncounterResolution.AUTO_BATTLE:
        hero = await _common.load_battle_vibemon(sess, hero_vibemon_id)
        wild = await _common.load_battle_vibemon(sess, selection.vibemon_id)
        opponent_id = uuid.uuid7()
        battle = _common.simulate_battle(
            hero,
            wild,
            trainer_a_id=trainer_id,
            trainer_b_id=opponent_id,
            trainer_a_name=username or f"trainer-{str(trainer_id)[:8]}",
            trainer_b_name="wild",
            rng_seed=rng_seed,
        )
        outcome = (
            WildEncounterOutcomeT.WIN_NO_ADOPT
            if battle["winner_trainer_id"] == str(trainer_id)
            else WildEncounterOutcomeT.DEFEAT
        )

    await wild_encounter_workflow.record_wild_encounter_outcome(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        vibemon_id=selection.vibemon_id,
        outcome=outcome,
    )
    return {
        "experience": "wild_encounter",
        "trainer_id": str(trainer_id),
        "hero_vibemon_id": str(hero_vibemon_id),
        "generated_wild_ids": [str(id_) for id_ in generated_wild],
        "selection": selection,
        "outcome": outcome.value,
        "battle": battle,
    }


async def _generate_owned_hero(
    sess: AsyncSession,
    *,
    trainer_id: uuid.UUID,
    latitude: float,
    longitude: float,
    timestamp: str | None,
) -> uuid.UUID:
    candidate = await candidate_workflow.generate_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        birth_seed=_common.birth_seed(latitude=latitude, longitude=longitude, timestamp=timestamp),
        bypass_credits=True,
    )
    adopted = await candidate_workflow.adopt_candidate(
        sess,
        trainer_id=_common.trainer_id(trainer_id),
        vibemon_id=candidate.id,
    )
    return adopted.id


async def _load_strength_row(sess: AsyncSession, vibemon_id: uuid.UUID):
    from app.storage.database import repositories

    return await repositories.load_vibemon(sess, vibemon_id)


def _manual_outcome(resolution: EncounterResolution) -> WildEncounterOutcomeT:
    if resolution is EncounterResolution.RUN:
        return WildEncounterOutcomeT.RUN
    if resolution is EncounterResolution.DEFEAT:
        return WildEncounterOutcomeT.DEFEAT
    if resolution is EncounterResolution.WIN_NO_ADOPT:
        return WildEncounterOutcomeT.WIN_NO_ADOPT
    raise ValueError("auto_battle resolution must be resolved by battle")


if __name__ == "__main__":
    app()
