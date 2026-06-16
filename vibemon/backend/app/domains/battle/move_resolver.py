"""Deep move resolution: one interface for Battle Action → Battle Events."""

import random

from app.domains.battle import entity, events, turn
from app.domains.battle.mechanics import accuracy, damage, effects, targeting
from app.domains.move.types import MoveCategoryT, MoveTargetT, VibemonTypeT

_BREAKING_POINT_ID = "universal.breaking_point"


class MoveResolver:
    """Resolve one move use into ordered battle events."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng

    def resolve(self, ctx: turn.Turn, use: turn.MoveUse) -> list[events.TurnEvent]:
        turn_events: list[events.TurnEvent] = []
        if use.move.pp_current <= 0:
            if all(move.pp_current <= 0 for move in use.user.battle_moves):
                use = use.model_copy(update={"move": _breaking_point_move()})
            else:
                turn_events.append(
                    events.MoveFailedEvent(user=use.user.name, move=use.move.name, reason="no_pp")
                )
                return turn_events

        use.move.pp_current -= 1
        targets = targeting.resolve_targets(ctx, use)
        turn_events.append(
            events.MoveUsedEvent(user=use.user.name, move=use.move.name, targets=tuple(t.name for t in targets))
        )
        if not targets and use.move.target != MoveTargetT.FIELD:
            turn_events.append(events.MoveFailedEvent(user=use.user.name, move=use.move.name, reason="no_targets"))
            return turn_events

        for target in targets:
            hit_events, hit = self._resolve_hit(ctx, use, target, spread=len(targets) > 1)
            turn_events.extend(hit_events)
            if hit.hit:
                effects.apply_effects_for_trigger(ctx, use, target, "on_hit", damage_dealt=hit.damage)
                effects.apply_effects_for_trigger(ctx, use, target, "after_damage", damage_dealt=hit.damage)

        if use.move.target == MoveTargetT.FIELD:
            effects.apply_effects_for_trigger(ctx, use, use.user, "on_use")

        return turn_events

    def _resolve_hit(
        self,
        ctx: turn.Turn,
        use: turn.MoveUse,
        target: entity.BattleVibemon,
        *,
        spread: bool,
    ) -> tuple[list[events.TurnEvent], turn.HitResult]:
        if not accuracy.hits(ctx, use, target):
            return (
                [events.MoveMissedEvent(user=use.user.name, move=use.move.name, target=target.name)],
                turn.HitResult(use=use, target=target, hit=False),
            )

        if use.move.category == MoveCategoryT.STATUS or use.move.power is None:
            return ([], turn.HitResult(use=use, target=target, damage=0, hit=True))

        result = damage.calc_damage(ctx, use.user, target, use.move, spread=spread)
        hit_events: list[events.TurnEvent] = []
        if result.damage > 0:
            target.current_hp = max(0, target.current_hp - result.damage)
            hit_events.append(
                events.DamageEvent(
                    source=use.user.name,
                    target=target.name,
                    move=use.move.name,
                    amount=result.damage,
                    hp_after=target.current_hp,
                    is_crit=result.is_crit,
                    effectiveness=result.effectiveness,
                    modifiers=damage.flatten_modifiers(result),
                )
            )
        return (
            hit_events,
            turn.HitResult(
                use=use,
                target=target,
                damage=result.damage,
                hit=result.blocked_reason is None,
                damage_result=result,
            ),
        )


def _breaking_point_move() -> entity.BattleMove:
    return entity.BattleMove(
        id=_BREAKING_POINT_ID,
        name="Breaking Point",
        flavor_text="A desperate all-out strike used when no moves have PP remaining; the user takes minor recoil.",
        type=VibemonTypeT.NORMAL,
        category=MoveCategoryT.PHYSICAL,
        power=50,
        accuracy=1.0,
        pp=1,
        effects=(
            {
                "chance": 1.0,
                "trigger": "after_damage",
                "effects": (
                    {
                        "kind": "recoil",
                        "ratio": 0.25,
                    },
                ),
            },
        ),
    )
