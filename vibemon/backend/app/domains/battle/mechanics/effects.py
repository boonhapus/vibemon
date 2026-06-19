from app.domains.battle import entity, events, turn
from app.domains.battle.mechanics import stats
from app.domains.move.entity import (
    Drain,
    EffectGroup,
    EffectTarget,
    Heal,
    Recoil,
    StatChange,
    StatusInflict,
    WeatherSet,
)
from app.domains.move.types import StatusConditionT


def _resolve_effect_target(
    effect_target: EffectTarget,
    use: turn.MoveUse,
    target: entity.BattleVibemon,
) -> tuple[entity.BattleVibemon, ...]:
    if effect_target == "self":
        return (use.user,)
    if effect_target in ("target", "all_targets"):
        return (target,)
    return ()


def apply_effect_group(
    ctx: turn.Turn,
    use: turn.MoveUse,
    target: entity.BattleVibemon,
    group: EffectGroup,
    *,
    damage_dealt: int = 0,
) -> None:
    """Roll and apply a shared-chance effect group."""
    if ctx.rng.random() >= group.chance:
        return

    for effect in group.effects:
        match effect:
            case StatusInflict():
                for recipient in _resolve_effect_target(effect.target, use, target):
                    if recipient.status == StatusConditionT.NONE:
                        recipient.status = effect.status
                        ctx.events.append(
                            events.StatusInflictedEvent(
                                source=use.user.name, target=recipient.name, status=effect.status
                            )
                        )
            case StatChange():
                for recipient in _resolve_effect_target(effect.target, use, target):
                    if recipient.current_hp <= 0:
                        continue
                    for stat_name, change in effect.changes.items():
                        if not hasattr(recipient.stat_stages, stat_name):
                            continue
                        current = getattr(recipient.stat_stages, stat_name)
                        updated = stats.clamp_stage(current + change)
                        if updated == current:
                            continue
                        setattr(recipient.stat_stages, stat_name, updated)
                        ctx.events.append(
                            events.StatChangeEvent(
                                source=use.user.name,
                                target=recipient.name,
                                changes={stat_name: updated - current},
                            )
                        )
            case Drain():
                if damage_dealt > 0:
                    amount = max(1, int(damage_dealt * effect.ratio))
                    use.user.current_hp = min(use.user.max_hp, use.user.current_hp + amount)
                    ctx.events.append(
                        events.HealEvent(
                            source=use.user.name, target=use.user.name, amount=amount, hp_after=use.user.current_hp
                        )
                    )
            case Recoil(basis="max_hp"):
                amount = max(1, int(use.user.max_hp * effect.ratio))
                use.user.current_hp = max(0, use.user.current_hp - amount)
                ctx.events.append(
                    events.DamageEvent(
                        source=use.user.name,
                        target=use.user.name,
                        amount=amount,
                        hp_after=use.user.current_hp,
                        is_crit=False,
                        effectiveness=1.0,
                    )
                )
            case Recoil():
                if damage_dealt > 0:
                    amount = max(1, int(damage_dealt * effect.ratio))
                    use.user.current_hp = max(0, use.user.current_hp - amount)
                    ctx.events.append(
                        events.DamageEvent(
                            source=use.user.name,
                            target=use.user.name,
                            amount=amount,
                            hp_after=use.user.current_hp,
                            is_crit=False,
                            effectiveness=1.0,
                        )
                    )
            case WeatherSet():
                ctx.battle.field.weather.kind = effect.weather
                ctx.battle.field.weather.turns_remaining = effect.turns
                ctx.events.append(
                    events.WeatherSetEvent(source=use.user.name, weather=effect.weather, turns=effect.turns)
                )
            case Heal():
                for recipient in _resolve_effect_target(effect.target, use, target):
                    amount = max(1, int(recipient.max_hp * effect.ratio))
                    recipient.current_hp = min(recipient.max_hp, recipient.current_hp + amount)
                    ctx.events.append(
                        events.HealEvent(
                            source=use.user.name, target=recipient.name, amount=amount, hp_after=recipient.current_hp
                        )
                    )


def apply_effects_for_trigger(
    ctx: turn.Turn,
    use: turn.MoveUse,
    target: entity.BattleVibemon,
    trigger: str,
    *,
    damage_dealt: int = 0,
) -> None:
    """Apply all move effects for a trigger."""
    for group in use.move.effects:
        if group.trigger == trigger:
            apply_effect_group(ctx, use, target, group, damage_dealt=damage_dealt)
