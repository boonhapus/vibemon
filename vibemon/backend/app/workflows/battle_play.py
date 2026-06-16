"""Interactive wild battle sessions backed by the domain engine."""

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ActiveBattle:
    battle_id: uuid.UUID
    trainer_id: TrainerIdT
    hero_vibemon_id: uuid.UUID
    wild_vibemon_id: uuid.UUID
    engine: engine.GameEngine
    player_trainer_id: TrainerIdT


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


async def finish_battle(
    sess: AsyncSession,
    *,
    session: ActiveBattle,
    registry: BattleSessionRegistry | None = None,
    now: dt.datetime | None = None,
) -> progression_engine.BattleProgressionResult:
    """Persist XP and progression once an interactive battle has concluded."""
    from app.workflows import battle_progression

    result = await battle_progression.persist_battle_progression(
        sess,
        battle=session.engine.battle,
        battle_id=session.battle_id,
        now=now,
    )
    if registry is not None:
        registry.remove(session.battle_id, trainer_id=session.trainer_id)
    return result


async def finish_concluded_battle(
    sess: AsyncSession,
    *,
    battle: entity.Battle,
    battle_id: uuid.UUID,
    now: dt.datetime | None = None,
) -> progression_engine.BattleProgressionResult:
    """Persist XP and progression for any concluded battle engine state."""
    from app.workflows import battle_progression

    return await battle_progression.persist_battle_progression(
        sess,
        battle=battle,
        battle_id=battle_id,
        now=now,
    )


def events_to_messages(events: list[events.TurnEvent]) -> list[str]:
    messages: list[str] = []
    for event in events:
        match event.kind:
            case "move_used":
                messages.append(f"{event.user} used {event.move}!")
            case "move_missed":
                messages.append(f"{event.move} missed {event.target}!")
            case "move_failed":
                reason = event.reason or "The move failed."
                messages.append(reason)
            case "damage":
                crit = " A critical hit!" if event.is_crit else ""
                messages.append(f"It dealt {event.amount} damage.{crit}")
            case "faint":
                messages.append(f"{event.target} fainted!")
            case "status_inflicted":
                messages.append(f"{event.target} was afflicted with {event.status}!")
            case "status_damage":
                messages.append(f"{event.target} took {event.amount} status damage.")
            case "status_message":
                messages.append(event.message_key.replace("_", " ").capitalize())
            case "stat_change":
                messages.append(f"{event.target}'s stats changed.")
            case "heal":
                messages.append(f"{event.target} recovered {event.amount} HP.")
            case "weather_set":
                messages.append(f"The weather became {event.weather}.")
    return messages
