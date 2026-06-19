"""HTTP read models for battle state."""

import uuid

from app.core.ids import TrainerIdT
from app.core.schema import Schema
from app.domains.battle import entity, events
from app.domains.move import catalog as move_catalog
from app.domains.move import combat_hints as move_combat_hints
from app.domains.move.types import MoveCategoryT, StatStageNameT, StatusConditionT, VibemonTypeT, WeatherT
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.progression import engine as progression_engine
from app.domains.vibemon.progression import formulas as progression_formulas
from app.domains.vibemon.progression import stats as progression_stats
from app.domains.vibemon.progression.types import GrowthGroupT
from app.http.schemas import battle as battle_schemas
from app.workflows.battle_play import ActiveBattle


class BattleMoveRead(Schema):
    id: str
    name: str
    type: VibemonTypeT
    category: MoveCategoryT
    power: int | None
    accuracy: float | None
    pp_current: int
    pp_max: int
    effectiveness: float
    flavor_text: str
    combat_hints: tuple[str, ...] = ()


class BattleCombatantRead(Schema):
    vibemon_id: uuid.UUID
    name: str
    types: tuple[VibemonTypeT, ...]
    level: int
    current_hp: int
    max_hp: int
    xp: int
    xp_to_next: int
    moves: tuple[BattleMoveRead, ...]
    is_fainted: bool
    status: StatusConditionT
    stat_stages: dict[str, int]
    volatiles: dict[str, int]
    sprite_url: str | None
    xp_bar_ratio: float


class BattleStateRead(Schema):
    battle_id: uuid.UUID
    turn_number: int
    concluded: bool
    fled: bool
    player_trainer_id: TrainerIdT
    wild_vibemon_id: uuid.UUID
    player: BattleCombatantRead
    opponent: BattleCombatantRead
    weather: WeatherT
    winner_trainer_id: TrainerIdT | None


class BattleTurnRead(Schema):
    events: tuple[events.TurnEvent, ...]
    messages: tuple[str, ...]
    state: BattleStateRead


class BattleFinishRead(Schema):
    progression: dict[str, object] | None


class BattleProgressionResultRead(Schema):
    battle_id: uuid.UUID
    deltas: tuple[dict[str, object], ...]


def _xp_to_next(vibemon: entity.BattleVibemon) -> int:
    return progression_formulas.xp_to_next_level(
        level=vibemon.level,
        xp=vibemon.xp,
        growth_rate=vibemon.growth_rate,
    )


def _xp_bar_ratio(*, level: int, xp: int, growth_rate: GrowthGroupT) -> float:
    return progression_formulas.xp_bar_ratio(level=level, xp=xp, growth_rate=growth_rate)


def _stat_stages(vibemon: entity.BattleVibemon) -> dict[str, int]:
    stages = vibemon.stat_stages
    return {key: value for key, value in stages.model_dump().items() if value != 0}


def _volatiles(vibemon: entity.BattleVibemon) -> dict[str, int]:
    result: dict[str, int] = {}
    if vibemon.is_confused and vibemon.confusion_turns > 0:
        result["confusion"] = vibemon.confusion_turns
    if vibemon.bound_turns > 0:
        result["bound"] = vibemon.bound_turns
    if vibemon.is_seeded:
        result["leech_seed"] = 1
    if vibemon.taunt_turns > 0:
        result["taunt"] = vibemon.taunt_turns
    if vibemon.sleep_turns_remaining > 0:
        result["sleep"] = vibemon.sleep_turns_remaining
    return result


def _sprite_url(vibemon: entity.BattleVibemon, *, is_player: bool) -> str | None:
    aesthetic = vibemon.aesthetic
    if aesthetic is None:
        return None
    preferred = AssetKind.POSE_BATTLE_BACK if is_player else AssetKind.POSE_BATTLE_OPPONENT
    for kind in (preferred, AssetKind.REFERENCE):
        asset = aesthetic.assets.get(kind)
        if asset is not None:
            return f"/api/assets/{asset.key}"
    return None


def move_read(move: entity.BattleMove, *, opponent_elements: tuple[VibemonTypeT, ...]) -> BattleMoveRead:
    return BattleMoveRead(
        id=move.id,
        name=move.name,
        type=move.type,
        category=move.category,
        power=move.power,
        accuracy=move.accuracy,
        pp_current=move.pp_current,
        pp_max=move.pp,
        effectiveness=move_catalog.get_element_effectiveness(move.type, opponent_elements),
        flavor_text=move.flavor_text,
        combat_hints=move_combat_hints.move_combat_hints(move),
    )


def combatant_read(
    vibemon: entity.BattleVibemon,
    *,
    opponent_elements: tuple[VibemonTypeT, ...],
    is_player: bool,
) -> BattleCombatantRead:
    return BattleCombatantRead(
        vibemon_id=vibemon.id,
        name=vibemon.name,
        types=vibemon.elements,
        level=vibemon.level,
        current_hp=vibemon.current_hp,
        max_hp=vibemon.max_hp,
        xp=vibemon.xp,
        xp_to_next=_xp_to_next(vibemon),
        moves=tuple(move_read(move, opponent_elements=opponent_elements) for move in vibemon.battle_moves),
        is_fainted=vibemon.is_fainted,
        status=vibemon.status,
        stat_stages=_stat_stages(vibemon),
        volatiles=_volatiles(vibemon),
        sprite_url=_sprite_url(vibemon, is_player=is_player),
        xp_bar_ratio=_xp_bar_ratio(level=vibemon.level, xp=vibemon.xp, growth_rate=vibemon.growth_rate),
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
        fled=battle.fled_trainer_id is not None,
        player_trainer_id=player_trainer_id,
        wild_vibemon_id=wild_vibemon_id,
        player=combatant_read(player, opponent_elements=opponent.elements, is_player=True),
        opponent=combatant_read(opponent, opponent_elements=player.elements, is_player=False),
        weather=battle.field.weather.kind,
        winner_trainer_id=winner_id,
    )


def battle_turn_read(
    session: ActiveBattle,
    *,
    events: list[events.TurnEvent],
    player_trainer_id: TrainerIdT,
    wild_vibemon_id: uuid.UUID,
) -> BattleTurnRead:
    state = battle_state_read(
        session,
        player_trainer_id=player_trainer_id,
        wild_vibemon_id=wild_vibemon_id,
    )
    return BattleTurnRead(
        events=tuple(events),
        messages=tuple(
            events_to_messages(
                events,
                hero_name=state.player.name,
                wild_name=state.opponent.name,
            )
        ),
        state=state,
    )


_STAT_LABELS: dict[StatStageNameT, str] = {
    "attack": "Attack",
    "defense": "Defense",
    "sp_attack": "Sp. Atk",
    "sp_defense": "Sp. Def",
    "speed": "Speed",
    "accuracy": "Accuracy",
    "evasion": "Evasion",
}


def _stat_change_message(
    target: str,
    stat: StatStageNameT,
    delta: int,
    *,
    hero_name: str | None,
) -> str:
    label = _STAT_LABELS.get(stat, stat.replace("_", " ").title())
    subject = "Your" if hero_name is not None and target == hero_name else "Their"
    if delta > 0:
        verb = "risen sharply" if delta >= 2 else "risen"
    else:
        verb = "dropped sharply" if delta <= -2 else "dropped"
    return f"{subject} {label} has {verb}!"


def events_to_messages(
    events: list[events.TurnEvent],
    *,
    hero_name: str | None = None,
    wild_name: str | None = None,
) -> list[str]:
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
                messages.append(_faint_message(event.target, hero_name=hero_name, wild_name=wild_name))
            case "status_inflicted":
                messages.append(f"{event.target} was afflicted with {event.status}!")
            case "status_damage":
                messages.append(f"{event.target} took {event.amount} status damage.")
            case "status_message":
                messages.append(event.message_key.replace("_", " ").capitalize())
            case "stat_change":
                stat, delta = next(iter(event.changes.items()))
                messages.append(_stat_change_message(stat=stat, delta=delta, target=event.target, hero_name=hero_name))
            case "heal":
                messages.append(f"{event.target} recovered {event.amount} HP.")
            case "weather_set":
                messages.append(f"The weather became {event.weather}.")
            case "fled":
                messages.append("You slip away.")
    return messages


def battle_finish_read(
    result: progression_engine.BattleProgressionResult,
    *,
    hero_vibemon_id: uuid.UUID,
    pending_offers: tuple[progression_engine.MoveLearnOffer, ...] = (),
) -> battle_schemas.BattleFinishResponse:
    """Tailor the hero's progression delta into a HUD-friendly finish response."""
    hero_delta = next(
        (delta for delta in result.deltas if delta.vibemon_id == hero_vibemon_id and delta.xp_award is not None),
        None,
    )
    progression: battle_schemas.HeroProgressionRead | None = None
    if hero_delta is not None and hero_delta.xp_award is not None:
        award = hero_delta.xp_award
        growth_rate = hero_delta.vibemon.growth_rate
        stat_deltas: tuple[dict[str, int | str], ...] = ()
        if award.new_level > award.previous_level:
            stat_deltas = progression_stats.stat_deltas_for_level_up(
                hero_delta.vibemon.identity.base,
                previous_level=award.previous_level,
                new_level=award.new_level,
            )
        if award.new_level >= progression_formulas.MAX_LEVEL:
            xp_to_next = 0
        else:
            next_threshold = progression_formulas.xp_to_reach_level(award.new_level + 1, growth_rate=growth_rate)
            xp_to_next = max(0, next_threshold - award.new_xp)
        progression = battle_schemas.HeroProgressionRead(
            vibemon_id=award.vibemon_id,
            previous_xp=award.previous_xp,
            new_xp=award.new_xp,
            previous_level=award.previous_level,
            new_level=award.new_level,
            xp_to_next=xp_to_next,
            xp_bar_ratio=_xp_bar_ratio(level=award.new_level, xp=award.new_xp, growth_rate=growth_rate),
            leveled_up=award.new_level > award.previous_level,
            stat_deltas=stat_deltas,
        )
    return battle_schemas.BattleFinishResponse(
        progression=progression,
        move_offers=tuple(_move_learn_offer_read(offer) for offer in pending_offers),
    )


def _move_learn_offer_read(offer: progression_engine.MoveLearnOffer) -> battle_schemas.MoveLearnOfferRead:
    return battle_schemas.MoveLearnOfferRead(
        vibemon_id=offer.vibemon_id,
        vibemon_name=offer.vibemon_name,
        requires_replace=offer.requires_replace,
        moves=tuple(
            battle_schemas.MoveLearnOptionRead(
                id=move.id,
                name=move.name,
                type=move.type,
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                pp=move.pp,
                level_requirement=move.level_requirement,
                flavor_text=move.flavor_text,
                combat_hints=move_combat_hints.move_combat_hints(move),
            )
            for move in offer.moves
        ),
    )


def _faint_message(target: str, *, hero_name: str | None, wild_name: str | None) -> str:
    if wild_name is not None and target == wild_name:
        return f"The wild {target} faints."
    if hero_name is not None and target == hero_name:
        return f"{target} faints."
    return f"{target} fainted!"
