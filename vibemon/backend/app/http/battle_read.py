"""HTTP read models for battle state."""

import uuid

from app.core.ids import TrainerIdT
from app.core.schema import Schema
from app.domains.battle import entity, events
from app.domains.move.types import VibemonTypeT
from app.workflows.battle_play import ActiveBattle


class BattleMoveRead(Schema):
    name: str
    type: VibemonTypeT
    power: int | None
    pp_current: int
    pp_max: int


class BattleCombatantRead(Schema):
    vibemon_id: uuid.UUID
    name: str
    types: tuple[VibemonTypeT, ...]
    level: int
    current_hp: int
    max_hp: int
    moves: tuple[BattleMoveRead, ...]
    is_fainted: bool


class BattleStateRead(Schema):
    battle_id: uuid.UUID
    turn_number: int
    concluded: bool
    player_trainer_id: TrainerIdT
    wild_vibemon_id: uuid.UUID
    player: BattleCombatantRead
    opponent: BattleCombatantRead
    winner_trainer_id: TrainerIdT | None


class BattleTurnRead(Schema):
    events: tuple[events.TurnEvent, ...]
    messages: tuple[str, ...]
    state: BattleStateRead


def combatant_read(vibemon: entity.BattleVibemon) -> BattleCombatantRead:
    return BattleCombatantRead(
        vibemon_id=vibemon.id,
        name=vibemon.name,
        types=vibemon.elements,
        level=vibemon.level,
        current_hp=vibemon.current_hp,
        max_hp=vibemon.max_hp,
        moves=tuple(
            BattleMoveRead(
                name=move.name,
                type=move.type,
                power=move.power,
                pp_current=move.pp_current,
                pp_max=move.pp,
            )
            for move in vibemon.battle_moves
        ),
        is_fainted=vibemon.is_fainted,
    )


def battle_state_read(
    session: ActiveBattle,
    *,
    player_trainer_id: TrainerIdT,
    wild_vibemon_id: uuid.UUID,
) -> BattleStateRead:
    battle = session.engine.battle
    if player_trainer_id == battle.trainer_a.id:
        player = battle.trainer_a.active_vibemon
        opponent = battle.trainer_b.active_vibemon
    else:
        player = battle.trainer_b.active_vibemon
        opponent = battle.trainer_a.active_vibemon
    winner_id = None if battle.winner is None else battle.winner.id

    return BattleStateRead(
        battle_id=session.battle_id,
        turn_number=battle.turn_number,
        concluded=battle.concluded,
        player_trainer_id=player_trainer_id,
        wild_vibemon_id=wild_vibemon_id,
        player=combatant_read(player),
        opponent=combatant_read(opponent),
        winner_trainer_id=winner_id,
    )
