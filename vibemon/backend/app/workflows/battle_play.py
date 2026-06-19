"""Interactive wild battle sessions backed by the domain engine."""

from dataclasses import dataclass, field
from typing import cast
import datetime as dt
import random
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BattleUnavailable
from app.core.ids import TrainerIdT
from app.domains.battle import actions, ai, engine, entity, events
from app.domains.battle.entity import BattleVibemon
from app.domains.vibemon.progression import engine as progression_engine
from app.storage.database import mapper, vibemon_repo, wild_pool_repo


@dataclass
class ActiveBattle:
    battle_id: uuid.UUID
    trainer_id: TrainerIdT
    hero_vibemon_id: uuid.UUID
    wild_vibemon_id: uuid.UUID
    engine: engine.GameEngine
    player_trainer_id: TrainerIdT
    pending_move_offers: list[progression_engine.MoveLearnOffer] = field(default_factory=list)
    progression_applied: bool = False
    encounter_outcome_recorded: bool = False


class BattleSessionRegistry:
    def __init__(self) -> None:
        self._sessions: dict[uuid.UUID, ActiveBattle] = {}

    def create(self, session: ActiveBattle) -> None:
        self._sessions[session.battle_id] = session

    def get(self, battle_id: uuid.UUID, *, trainer_id: TrainerIdT) -> ActiveBattle:
        session = self._sessions.get(battle_id)
        if session is None or session.trainer_id != trainer_id:
            raise BattleUnavailable("Battle session not found.")
        return session

    def remove(self, battle_id: uuid.UUID, *, trainer_id: TrainerIdT) -> ActiveBattle | None:
        session = self._sessions.get(battle_id)
        if session is None or session.trainer_id != trainer_id:
            return None
        return self._sessions.pop(battle_id, None)


def pending_offer_for(
    session: ActiveBattle,
    *,
    vibemon_id: uuid.UUID,
) -> progression_engine.MoveLearnOffer | None:
    return next((offer for offer in session.pending_move_offers if offer.vibemon_id == vibemon_id), None)


def clear_pending_offer(session: ActiveBattle, *, vibemon_id: uuid.UUID) -> None:
    session.pending_move_offers = [offer for offer in session.pending_move_offers if offer.vibemon_id != vibemon_id]


def collect_owned_move_offers(
    result: progression_engine.BattleProgressionResult,
    *,
    player_trainer_id: TrainerIdT,
    hero_vibemon_id: uuid.UUID,
    battle: entity.Battle,
) -> tuple[progression_engine.MoveLearnOffer, ...]:
    """Order offers: active battler first, then bench by crew slot."""
    player_trainer = battle.trainer_a if battle.trainer_a.id == player_trainer_id else battle.trainer_b
    offer_by_id = {offer.vibemon_id: offer for delta in result.deltas for offer in delta.move_learn_offers}
    owned_crew = [combatant for combatant in player_trainer.crew if combatant.is_owned]
    owned_crew.sort(key=lambda combatant: (combatant.id != hero_vibemon_id, player_trainer.crew.index(combatant)))
    ordered: list[progression_engine.MoveLearnOffer] = []
    for combatant in owned_crew:
        offer = offer_by_id.get(combatant.id)
        if offer is not None:
            ordered.append(offer)
    return tuple(ordered)


async def load_battle_vibemon(sess: AsyncSession, vibemon_id: uuid.UUID) -> BattleVibemon:
    row = await vibemon_repo.load_vibemon(sess, vibemon_id)
    vibemon = await mapper.vibemon_from_row(row)
    combatant = BattleVibemon(**vibemon.model_dump())
    if not combatant.battle_moves:
        raise BattleUnavailable(f"{combatant.name} has no moves for battle.")
    return combatant


def wild_trainer_id(*, trainer_id: TrainerIdT, wild_vibemon_id: uuid.UUID) -> TrainerIdT:
    return uuid.uuid5(trainer_id, f"wild-{wild_vibemon_id}")


async def start_wild_battle(
    sess: AsyncSession,
    *,
    registry: BattleSessionRegistry,
    trainer_id: TrainerIdT,
    trainer_name: str,
    hero_vibemon_id: uuid.UUID,
    wild_vibemon_id: uuid.UUID,
) -> ActiveBattle:
    hero_row = await vibemon_repo.load_vibemon(sess, hero_vibemon_id)
    if hero_row.trainer_id != trainer_id:
        raise BattleUnavailable("That Vibemon is not in your crew.")

    if not await wild_pool_repo.is_wild_encounter_eligible(sess, vibemon_id=wild_vibemon_id):
        raise BattleUnavailable("That Wild Vibemon is no longer available.")

    hero = await load_battle_vibemon(sess, hero_vibemon_id)
    wild = await load_battle_vibemon(sess, wild_vibemon_id)
    opponent_id = wild_trainer_id(trainer_id=trainer_id, wild_vibemon_id=wild_vibemon_id)

    game = engine.GameEngine(
        entity.BattleTrainer(id=trainer_id, username=trainer_name, crew=[hero]),
        entity.BattleTrainer(id=opponent_id, username="Wild", crew=[wild]),
    )
    battle_id = uuid.uuid7()
    session = ActiveBattle(
        battle_id=battle_id,
        trainer_id=trainer_id,
        hero_vibemon_id=hero_vibemon_id,
        wild_vibemon_id=wild_vibemon_id,
        engine=game,
        player_trainer_id=trainer_id,
    )
    registry.create(session)
    return session


def submit_player_turn(
    session: ActiveBattle,
    *,
    move_name: str,
) -> list[events.TurnEvent]:
    battle = session.engine.battle
    if battle.concluded:
        raise BattleUnavailable("Battle is already over.")

    player_trainer = battle.trainer_a if session.player_trainer_id == battle.trainer_a.id else battle.trainer_b
    wild_trainer = battle.trainer_b if player_trainer is battle.trainer_a else battle.trainer_a

    player_move = actions.MoveAction(trainer=player_trainer.id, move_name=move_name)
    wild_move = ai.wild_move_action(wild_trainer, rng=random.Random())

    return session.engine.submit_actions([player_move, wild_move])


def submit_player_run(session: ActiveBattle) -> list[events.TurnEvent]:
    battle = session.engine.battle
    if battle.concluded:
        raise BattleUnavailable("Battle is already over.")
    battle.fled_trainer_id = session.player_trainer_id
    return [events.FledEvent(trainer_id=str(session.player_trainer_id))]


def submit_player_switch(
    session: ActiveBattle,
    *,
    bench_index: int,
) -> list[events.TurnEvent]:
    battle = session.engine.battle
    if battle.concluded:
        raise BattleUnavailable("Battle is already over.")

    player_trainer = battle.trainer_a if session.player_trainer_id == battle.trainer_a.id else battle.trainer_b
    wild_trainer = battle.trainer_b if player_trainer is battle.trainer_a else battle.trainer_a

    if bench_index < 0 or bench_index >= len(player_trainer.crew):
        raise BattleUnavailable("That crew member is not in this battle.")
    bench_vibemon = cast(BattleVibemon, player_trainer.crew[bench_index])
    if bench_vibemon.is_fainted:
        raise BattleUnavailable("That Vibemon cannot battle.")
    if bench_index == player_trainer.active_index:
        raise BattleUnavailable("That Vibemon is already active.")

    player_trainer.active_index = bench_index
    wild_move = ai.wild_move_action(wild_trainer, rng=random.Random())
    switch_action = actions.SwitchAction(trainer=player_trainer.id, bench_index=bench_index)
    return session.engine.submit_actions([switch_action, wild_move])


async def finish_battle(
    sess: AsyncSession,
    *,
    session: ActiveBattle | None = None,
    battle: entity.Battle | None = None,
    battle_id: uuid.UUID | None = None,
    registry: BattleSessionRegistry | None = None,
    now: dt.datetime | None = None,
) -> progression_engine.BattleProgressionResult:
    """Persist battle progression after conclusion.

    Pass ``session`` for interactive battles (move offers, registry lifecycle).
    Pass ``battle`` and ``battle_id`` alone for headless simulators.
    """
    from app.workflows import battle_progression

    if session is not None:
        resolved_battle = session.engine.battle
        resolved_battle_id = session.battle_id
    elif battle is not None and battle_id is not None:
        resolved_battle = battle
        resolved_battle_id = battle_id
    else:
        raise BattleUnavailable("Provide session or both battle and battle_id.")

    if session is not None:
        if session.progression_applied:
            return progression_engine.BattleProgressionResult(
                battle_id=resolved_battle_id,
                deltas=(),
            )
        if resolved_battle.fled_trainer_id is not None:
            if registry is not None:
                registry.remove(resolved_battle_id, trainer_id=session.trainer_id)
            return progression_engine.BattleProgressionResult(battle_id=resolved_battle_id, deltas=())

    result = await battle_progression.persist_battle_progression(
        sess,
        battle=resolved_battle,
        battle_id=resolved_battle_id,
        now=now,
    )

    if session is None:
        return result

    session.progression_applied = True
    owned_offers = collect_owned_move_offers(
        result,
        player_trainer_id=session.player_trainer_id,
        hero_vibemon_id=session.hero_vibemon_id,
        battle=resolved_battle,
    )
    session.pending_move_offers = list(owned_offers)
    if registry is not None and not session.pending_move_offers:
        registry.remove(resolved_battle_id, trainer_id=session.trainer_id)
    return result


async def accept_pending_move_learn(
    sess: AsyncSession,
    *,
    session: ActiveBattle,
    registry: BattleSessionRegistry,
    vibemon_id: uuid.UUID,
    move_content_id: str,
    replace_content_id: str | None = None,
    now: dt.datetime | None = None,
) -> None:
    from app.workflows import battle_progression

    if not session.progression_applied:
        raise BattleUnavailable("Battle progression has not been applied yet.")
    offer = pending_offer_for(session, vibemon_id=vibemon_id)
    if offer is None:
        raise BattleUnavailable("No pending move offer for that Vibemon.")
    await battle_progression.accept_move_learn(
        sess,
        trainer_id=session.trainer_id,
        vibemon_id=vibemon_id,
        move_content_id=move_content_id,
        replace_content_id=replace_content_id,
        pending_offer=offer,
        now=now,
    )
    clear_pending_offer(session, vibemon_id=vibemon_id)
    if not session.pending_move_offers:
        registry.remove(session.battle_id, trainer_id=session.trainer_id)


async def decline_pending_move_learn(
    sess: AsyncSession,
    *,
    session: ActiveBattle,
    registry: BattleSessionRegistry,
    vibemon_id: uuid.UUID,
    now: dt.datetime | None = None,
) -> None:
    from app.workflows import battle_progression

    if not session.progression_applied:
        raise BattleUnavailable("Battle progression has not been applied yet.")
    offer = pending_offer_for(session, vibemon_id=vibemon_id)
    if offer is None:
        raise BattleUnavailable("No pending move offer for that Vibemon.")
    await battle_progression.decline_move_learn(
        sess,
        trainer_id=session.trainer_id,
        vibemon_id=vibemon_id,
        pending_offer=offer,
        now=now,
    )
    clear_pending_offer(session, vibemon_id=vibemon_id)
    if not session.pending_move_offers:
        registry.remove(session.battle_id, trainer_id=session.trainer_id)
