from __future__ import annotations

from collections.abc import Sequence
import random

import pydantic

from app import types
from app.battle import actions, events, hooks, scripts, turn
from app.battle import schema as battle_schema
from app.battle.rules import accuracy, damage, effects, status, targeting, turn_order


class GameEngine:
    """Stateless battle engine pipeline; Battle owns persistent combat state."""

    def __init__(
        self,
        trainer_a: battle_schema.BattleTrainer,
        trainer_b: battle_schema.BattleTrainer,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self.hooks = hooks.HookRegistry()
        self.scripts = scripts.MoveScriptRegistry()
        self.battle = battle_schema.Battle(
            trainer_a=_coerce_trainer(trainer_a),
            trainer_b=_coerce_trainer(trainer_b),
            turn_number=1,
            turn_history=[],
        )

    def submit_actions(self, submitted_actions: Sequence[actions.BattleAction]) -> list[events.TurnEvent]:
        """Process a turn from self-identifying tagged actions."""
        ctx = turn.Turn.from_submit(self.battle, self._rng, tuple(submitted_actions))
        targeting.validate_actions(ctx)
        self._record_turn_start(ctx)
        self._build_execution_stack(ctx)
        self._execute_stack(ctx)
        self._end_of_turn(ctx)
        self._finish_turn(ctx)
        self.battle.turn_history[-1].events = ctx.events
        return ctx.events

    def _record_turn_start(self, ctx: turn.Turn) -> None:
        ctx.phase = "turn_start"
        self.battle.turn_history.append(
            battle_schema.TurnRecord(
                turn_number=self.battle.turn_number,
                actions=list(ctx.actions),
                events=[],
            )
        )

    def _build_execution_stack(self, ctx: turn.Turn) -> None:
        ctx.phase = "action_sorting"
        ctx.stack = turn_order.resolve_turn_order(ctx)

    def _execute_stack(self, ctx: turn.Turn) -> None:
        ctx.phase = "execute_stack"
        for entry in list(ctx.stack):
            ctx.current_entry = entry
            if self.battle.concluded:
                break
            if entry.actor.is_fainted:
                continue
            if not isinstance(entry.action, actions.MoveAction):
                continue

            pre_action = status.check_pre_action(ctx, entry.actor)
            ctx.events.extend(pre_action.events)
            if pre_action.blocked:
                continue

            self._execute_move_use(ctx, targeting.make_move_use(ctx, entry, entry.action))
            if entry.opponent.is_fainted:
                ctx.events.append(events.FaintEvent(target=entry.opponent.name))
                break

    def _execute_move_use(self, ctx: turn.Turn, use: turn.MoveUse) -> None:
        use.move.pp_current -= 1
        targets = targeting.resolve_targets(ctx, use)
        ctx.events.append(
            events.MoveUsedEvent(user=use.user.name, move=use.move.name, targets=tuple(t.name for t in targets))
        )
        if not targets and use.move.target != types.MoveTargetT.FIELD:
            ctx.events.append(events.MoveFailedEvent(user=use.user.name, move=use.move.name, reason="no_targets"))
            return

        for target in targets:
            hit = self._execute_hit(ctx, use, target, spread=len(targets) > 1)
            if hit.hit:
                effects.apply_effects_for_trigger(ctx, use, target, "on_hit", damage_dealt=hit.damage)
                effects.apply_effects_for_trigger(ctx, use, target, "after_damage", damage_dealt=hit.damage)

        if use.move.target == types.MoveTargetT.FIELD:
            effects.apply_effects_for_trigger(ctx, use, use.user, "on_use")

    def _execute_hit(
        self,
        ctx: turn.Turn,
        use: turn.MoveUse,
        target: battle_schema.BattleVibemon,
        *,
        spread: bool,
    ) -> turn.HitResult:
        if not accuracy.hits(ctx, use, target):
            ctx.events.append(events.MoveMissedEvent(user=use.user.name, move=use.move.name, target=target.name))
            return turn.HitResult(use=use, target=target, hit=False)

        if use.move.category == types.MoveCategoryT.STATUS or use.move.power is None:
            return turn.HitResult(use=use, target=target, damage=0, hit=True)

        result = damage.calc_damage(ctx, use.user, target, use.move, spread=spread)
        if result.damage > 0:
            target.current_hp = max(0, target.current_hp - result.damage)
            ctx.events.append(
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
        return turn.HitResult(
            use=use, target=target, damage=result.damage, hit=result.blocked_reason is None, damage_result=result
        )

    def _end_of_turn(self, ctx: turn.Turn) -> None:
        ctx.phase = "end_of_turn"
        active = (self.battle.trainer_a.active_vibemon, self.battle.trainer_b.active_vibemon)
        for vibemon in active:
            if status_damage := status.apply_status_damage(vibemon):
                ctx.events.append(
                    events.StatusDamageEvent(target=vibemon.name, amount=status_damage, hp_after=vibemon.current_hp)
                )
                if vibemon.is_fainted:
                    ctx.events.append(events.FaintEvent(target=vibemon.name))

        for vibemon in sorted(active, key=turn_order.stats.effective_speed, reverse=True):
            ctx.events.extend(status.end_of_turn_maintenance(vibemon))

    def _finish_turn(self, ctx: turn.Turn) -> None:
        ctx.phase = "turn_end"
        self.battle.turn_number += 1
        winner = determine_winner(self.battle)
        if not winner:
            a = self.battle.trainer_a.active_vibemon
            b = self.battle.trainer_b.active_vibemon
            if a.is_fainted and b.is_fainted:
                winner = self.battle.trainer_b
        if winner:
            self.battle.winner = winner


def _coerce_trainer(trainer: object) -> battle_schema.BattleTrainer:
    if isinstance(trainer, battle_schema.BattleTrainer):
        return trainer
    if isinstance(trainer, pydantic.BaseModel):
        return battle_schema.BattleTrainer(**trainer.model_dump())
    return battle_schema.BattleTrainer.model_validate(trainer)


def determine_winner(battle: battle_schema.Battle) -> battle_schema.BattleTrainer | None:
    """Return winning trainer if opponent's active vibemon fainted."""
    if battle.trainer_a.active_vibemon.is_fainted:
        return battle.trainer_b
    if battle.trainer_b.active_vibemon.is_fainted:
        return battle.trainer_a
    return None
