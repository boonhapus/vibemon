"""Actual Encounter HTTP routes."""

import uuid

from litestar import Request, Router, get, post
from litestar.datastructures import State
from litestar.exceptions import ClientException
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.vibemon.strength import member_strength
from app.http import battle_read, deps
from app.http.schemas import encounters as encounter_schemas
from app.storage.database import vibemon_repo
from app.workflows import actual_encounter


@post("/start")
async def start_encounter(
    request: Request[object, object, State],
    data: encounter_schemas.EncounterStartBody,
    db: AsyncSession,
) -> encounter_schemas.EncounterStartResponse:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    hero_row = await vibemon_repo.load_vibemon(db, data.hero_vibemon_id)
    if hero_row.trainer_id != trainer.id:
        raise ClientException(detail="That Vibemon is not in your crew.")

    started = await actual_encounter.start_actual_encounter(
        db,
        registry=registry,
        trainer_id=trainer.id,
        trainer_name=trainer.username,
        hero_vibemon_id=data.hero_vibemon_id,
        latitude=data.latitude,
        longitude=data.longitude,
        crew_strength=member_strength(hero_row),  # pyrefly: ignore
        desired_supply=data.desired_supply,
    )
    if started is None:
        raise ClientException(detail="No Wild Vibemon are available nearby.")

    state = battle_read.battle_state_read(
        started.session,
        player_trainer_id=started.session.player_trainer_id,
        wild_vibemon_id=started.session.wild_vibemon_id,
    )
    return encounter_schemas.EncounterStartResponse(
        selection=started.selection,
        battle=state,
    )


@get("/{battle_id:uuid}")
async def get_encounter_battle(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    db: AsyncSession,
) -> battle_read.BattleStateRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    return battle_read.battle_state_read(
        session,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


@post("/{battle_id:uuid}/turns")
async def submit_encounter_turn(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: encounter_schemas.EncounterTurnBody,
    db: AsyncSession,
) -> battle_read.BattleTurnRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    return actual_encounter.submit_encounter_turn(session, move_name=data.move_name)


@post("/{battle_id:uuid}/conclude")
async def conclude_encounter(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: encounter_schemas.EncounterConcludeBody,
    db: AsyncSession,
) -> encounter_schemas.EncounterConcludeResponse:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    conclusion = await actual_encounter.conclude_actual_encounter(
        db,
        registry=registry,
        session=session,
        trainer_id=trainer.id,
        outcome=data.outcome,
    )
    await db.commit()
    return encounter_schemas.EncounterConcludeResponse(
        outcome=conclusion.outcome,
        progression=conclusion.progression,
    )


encounter_router = Router(
    path="/api/encounters",
    route_handlers=[
        start_encounter,
        get_encounter_battle,
        submit_encounter_turn,
        conclude_encounter,
    ],
)
