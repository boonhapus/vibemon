"""Wild battle HTTP routes."""

import uuid

from litestar import Request, Response, Router, get, post
from litestar.datastructures import State
from litestar.exceptions import ClientException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BattleUnavailable
from app.domains.encounter.types import WildEncounterOutcomeT
from app.http import battle_read, deps
from app.http.schemas import battle as battle_schemas
from app.workflows import actual_encounter, battle_play, wild_encounter
from app.workflows.battle_play import finish_battle


@post("")
async def start_battle(
    request: Request[object, object, State],
    data: battle_schemas.BattleStartBody,
    db: AsyncSession,
) -> battle_read.BattleStateRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    session = await battle_play.start_wild_battle(
        db,
        registry=registry,
        trainer_id=trainer.id,
        trainer_name=trainer.username,
        hero_vibemon_id=data.hero_vibemon_id,
        wild_vibemon_id=data.wild_vibemon_id,
    )
    return battle_read.battle_state_read(
        session,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


@get("/{battle_id:uuid}")
async def get_battle(
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


@post("/{battle_id:uuid}/turn")
async def submit_battle_turn(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: battle_schemas.BattleTurnBody,
    db: AsyncSession,
) -> battle_read.BattleTurnRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    try:
        turn_events = battle_play.submit_player_turn(session, move_name=data.move_name)
    except BattleUnavailable as exc:
        raise ClientException(detail=str(exc)) from exc
    except ValueError as exc:
        raise ClientException(detail=str(exc)) from exc
    return battle_read.battle_turn_read(
        session,
        events=turn_events,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


@post("/{battle_id:uuid}/run")
async def submit_battle_run(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    db: AsyncSession,
) -> battle_read.BattleTurnRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    try:
        turn_events = battle_play.submit_player_run(session)
    except BattleUnavailable as exc:
        raise ClientException(detail=str(exc)) from exc
    return battle_read.battle_turn_read(
        session,
        events=turn_events,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


@post("/{battle_id:uuid}/switch")
async def submit_battle_switch(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: battle_schemas.BattleSwitchBody,
    db: AsyncSession,
) -> battle_read.BattleTurnRead:
    trainer = await deps.load_authenticated_trainer(request, db)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    try:
        turn_events = battle_play.submit_player_switch(session, bench_index=data.bench_index)
    except BattleUnavailable as exc:
        raise ClientException(detail=str(exc)) from exc
    return battle_read.battle_turn_read(
        session,
        events=turn_events,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


@post("/{battle_id:uuid}/finish")
async def finish_battle_route(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    db: AsyncSession,
) -> battle_schemas.BattleFinishResponse:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    if not session.engine.battle.concluded:
        raise ClientException(detail="Battle is not concluded yet.")

    progression = await finish_battle(
        db,
        session=session,
        registry=registry,
    )

    if not session.encounter_outcome_recorded and (
        session.engine.battle.winner is not None or session.engine.battle.fled_trainer_id is not None
    ):
        if session.engine.battle.fled_trainer_id is not None:
            outcome = WildEncounterOutcomeT.RUN
        else:
            outcome = actual_encounter.encounter_outcome_from_battle(session)
        await wild_encounter.record_wild_encounter_outcome(
            db,
            trainer_id=trainer.id,
            vibemon_id=session.wild_vibemon_id,
            outcome=outcome,
        )
        session.encounter_outcome_recorded = True

    await db.commit()
    return battle_read.battle_finish_read(
        progression,
        hero_vibemon_id=session.hero_vibemon_id,
        pending_offers=tuple(session.pending_move_offers),
    )


@post("/{battle_id:uuid}/move-learn/accept")
async def accept_move_learn_route(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: battle_schemas.MoveLearnAcceptBody,
    db: AsyncSession,
) -> Response[None]:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    if not session.engine.battle.concluded:
        raise ClientException(detail="Battle is not concluded yet.")
    try:
        await battle_play.accept_pending_move_learn(
            db,
            session=session,
            registry=registry,
            vibemon_id=data.vibemon_id,
            move_content_id=data.move_content_id,
            replace_content_id=data.replace_content_id,
        )
    except BattleUnavailable as exc:
        raise ClientException(detail=str(exc)) from exc
    await db.commit()
    return Response(content=None, status_code=204)


@post("/{battle_id:uuid}/move-learn/decline")
async def decline_move_learn_route(
    battle_id: uuid.UUID,
    request: Request[object, object, State],
    data: battle_schemas.MoveLearnDeclineBody,
    db: AsyncSession,
) -> Response[None]:
    trainer = await deps.load_authenticated_trainer(request, db)
    registry = deps.battle_session_registry(request)
    session = deps.load_battle_session(request, battle_id=battle_id, trainer_id=trainer.id)
    if not session.engine.battle.concluded:
        raise ClientException(detail="Battle is not concluded yet.")
    try:
        await battle_play.decline_pending_move_learn(
            db,
            session=session,
            registry=registry,
            vibemon_id=data.vibemon_id,
        )
    except BattleUnavailable as exc:
        raise ClientException(detail=str(exc)) from exc
    await db.commit()
    return Response(content=None, status_code=204)


battle_router = Router(
    path="/api/battles",
    route_handlers=[
        start_battle,
        get_battle,
        submit_battle_turn,
        submit_battle_run,
        submit_battle_switch,
        finish_battle_route,
        accept_move_learn_route,
        decline_move_learn_route,
    ],
)
