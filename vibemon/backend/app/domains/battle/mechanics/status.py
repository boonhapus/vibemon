import pydantic

from app.core.schema import FrozenSchema
from app.domains.battle import const, entity, turn
from app.domains.battle import events as event_models
from app.domains.move.types import StatusConditionT


class PreActionResult(FrozenSchema):
    """Result of a pre-action check."""

    blocked: bool
    events: list[event_models.TurnEvent] = pydantic.Field(default_factory=list)


def check_pre_action(ctx: turn.Turn, vibemon: entity.BattleVibemon) -> PreActionResult:
    """Tick pre-action status/volatile effects in the fixed engine order."""
    if vibemon.is_fainted:
        return PreActionResult(blocked=True)

    if vibemon.status == StatusConditionT.SLEEP:
        vibemon.sleep_turns_remaining -= 1
        if vibemon.sleep_turns_remaining <= 0:
            vibemon.status = StatusConditionT.NONE
            return PreActionResult(
                blocked=False,
                events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="woke_up")],
            )
        return PreActionResult(
            blocked=True,
            events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="asleep")],
        )

    if vibemon.status == StatusConditionT.FREEZE:
        if ctx.rng.random() < const.FREEZE_THAW_CHANCE:
            vibemon.status = StatusConditionT.NONE
            return PreActionResult(
                blocked=False,
                events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="thawed")],
            )
        return PreActionResult(
            blocked=True,
            events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="frozen")],
        )

    if vibemon.is_flinched:
        vibemon.is_flinched = False
        return PreActionResult(
            blocked=True,
            events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="flinched")],
        )

    if vibemon.status == StatusConditionT.PARALYSIS and ctx.rng.random() < const.PARALYSIS_FULLY_PARALYZED_CHANCE:
        return PreActionResult(
            blocked=True,
            events=[event_models.StatusMessageEvent(target=vibemon.name, message_key="fully_paralyzed")],
        )

    if vibemon.is_confused and ctx.rng.random() < const.CONFUSION_SELF_HIT_CHANCE:
        damage = vibemon.max_hp // const.CONFUSION_SELF_HIT_DIVISOR
        vibemon.current_hp = max(0, vibemon.current_hp - damage)
        return PreActionResult(
            blocked=True,
            events=[
                event_models.DamageEvent(
                    source=vibemon.name,
                    target=vibemon.name,
                    amount=damage,
                    hp_after=vibemon.current_hp,
                    is_crit=False,
                    effectiveness=1.0,
                ),
                event_models.StatusMessageEvent(target=vibemon.name, message_key="confusion_self_hit"),
            ],
        )

    return PreActionResult(blocked=False)


def apply_status_damage(vibemon: entity.BattleVibemon) -> int:
    """Apply end-of-turn damage from burn, poison, or bad poison."""
    match vibemon.status:
        case StatusConditionT.BURN:
            damage = vibemon.max_hp // const.BURN_DAMAGE_DIVISOR
        case StatusConditionT.POISON:
            damage = vibemon.max_hp // const.POISON_DAMAGE_DIVISOR
        case StatusConditionT.BAD_POISON:
            vibemon.bad_poison_counter += 1
            damage = vibemon.max_hp * vibemon.bad_poison_counter // const.BURN_DAMAGE_DIVISOR
        case _:
            return 0
    vibemon.current_hp = max(0, vibemon.current_hp - damage)
    return damage


def end_of_turn_maintenance(vibemon: entity.BattleVibemon) -> list[event_models.TurnEvent]:
    """End-of-turn status expiry."""
    emitted: list[event_models.TurnEvent] = []

    if vibemon.is_confused:
        vibemon.confusion_turns -= 1
        if vibemon.confusion_turns <= 0:
            vibemon.is_confused = False
            emitted.append(event_models.StatusMessageEvent(target=vibemon.name, message_key="confusion_ended"))

    if vibemon.taunt_turns > 0:
        vibemon.taunt_turns -= 1
        if vibemon.taunt_turns <= 0:
            emitted.append(event_models.StatusMessageEvent(target=vibemon.name, message_key="taunt_ended"))

    if vibemon.bound_turns > 0:
        vibemon.bound_turns -= 1
        if vibemon.bound_turns <= 0:
            emitted.append(event_models.StatusMessageEvent(target=vibemon.name, message_key="bind_ended"))

    return emitted
