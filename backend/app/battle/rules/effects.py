from __future__ import annotations

from app import schema, types
from app.battle import events, turn
from app.battle import schema as battle_schema
from app.battle.rules import stats


def _resolve_effect_target(
    effect_target: schema.EffectTarget,
    use: turn.MoveUse,
    target: battle_schema.BattleVibemon,
) -> tuple[battle_schema.BattleVibemon, ...]:
    if effect_target == "self":
        return (use.user,)
    if effect_target in ("target", "all_targets"):
        return (target,)
    return ()


def apply_effect_group(
    ctx: turn.Turn,
    use: turn.MoveUse,
    target: battle_schema.BattleVibemon,
    group: schema.EffectGroup,
    *,
    damage_dealt: int = 0,
) -> None:
    """Roll and apply a shared-chance effect group."""
    if ctx.rng.random() >= group.chance:
        return

    for effect in group.effects:
        match effect:
            case schema.StatusInflict():
                for recipient in _resolve_effect_target(effect.target, use, target):
                    if recipient.status == types.StatusConditionT.NONE:
                        recipient.status = effect.status
                        ctx.events.append(
                            events.StatusInflictedEvent(
                                source=use.user.name, target=recipient.name, status=effect.status
                            )
                        )
            case schema.StatChange():
                for recipient in _resolve_effect_target(effect.target, use, target):
                    applied: dict[types.StatStageNameT, int] = {}
                    for stat_name, change in effect.changes.items():
                        if hasattr(recipient.stat_stages, stat_name):
                            current = getattr(recipient.stat_stages, stat_name)
                            setattr(recipient.stat_stages, stat_name, stats.clamp_stage(current + change))
                            applied[stat_name] = change
                    if applied:
                        ctx.events.append(
                            events.StatChangeEvent(source=use.user.name, target=recipient.name, changes=applied)
                        )
            case schema.Drain():
                if damage_dealt > 0:
                    amount = max(1, int(damage_dealt * effect.ratio))
                    use.user.current_hp = min(use.user.max_hp, use.user.current_hp + amount)
                    ctx.events.append(
                        events.HealEvent(
                            source=use.user.name, target=use.user.name, amount=amount, hp_after=use.user.current_hp
                        )
                    )
            case schema.Recoil():
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
            case schema.WeatherSet():
                ctx.battle.field.weather.kind = effect.weather
                ctx.battle.field.weather.turns_remaining = effect.turns
                ctx.events.append(
                    events.WeatherSetEvent(source=use.user.name, weather=effect.weather, turns=effect.turns)
                )
            case schema.Heal():
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
    target: battle_schema.BattleVibemon,
    trigger: str,
    *,
    damage_dealt: int = 0,
) -> None:
    """Apply all move effects for a trigger."""
    for group in use.move.effects:
        if group.trigger == trigger:
            apply_effect_group(ctx, use, target, group, damage_dealt=damage_dealt)
