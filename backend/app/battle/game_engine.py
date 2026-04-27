"""Battle engine implementing the Pokémon-style turn-based combat state machine."""

from collections.abc import Sequence
import abc
import enum
import random

import pydantic
from pydantic import BaseModel

from app import const, schema, types
from app.balance import element_chart

type StackEntry = tuple[schema.BattleVibemon, schema.BattleVibemon, schema.BattleAction]


class Phase(enum.Enum):
    """Explicit battle engine phases per spec."""

    ACTION_SORTING = "action_sorting"
    PRE_ACTION_CHECKS = "pre_action_checks"
    EXECUTE_STACK = "execute_stack"
    END_OF_TURN = "end_of_turn"
    TURN_END = "turn_end"


class BattleStateMachine:
    """State machine owning transient execution state."""

    def __init__(self, battle: schema.Battle, rng: random.Random) -> None:
        self.battle = battle
        self.rng = rng
        self._events: list[schema.TurnEvent] = []
        self._phase: Phase = Phase.ACTION_SORTING
        self._execution_stack: list[StackEntry] = []
        self._stack_index: int = 0

    def transition(self, to: Phase) -> None:
        """Move state machine to given phase."""
        self._phase = to

    def set_execution_stack(self, stack: Sequence[StackEntry]) -> None:
        """Replace execution stack and reset index to zero."""
        self._execution_stack = list(stack)
        self._stack_index = 0

    @property
    def events(self) -> list[schema.TurnEvent]:
        """Return a copy to prevent external mutation."""
        return self._events.copy()

    @property
    def current_phase(self) -> Phase:
        """Current phase of battle execution."""
        return self._phase

    @property
    def current_stack_entry(self) -> StackEntry | None:
        """Current (attacker, defender, action) entry, or None if exhausted."""
        if self._stack_index < len(self._execution_stack):
            return self._execution_stack[self._stack_index]
        return None

    def advance_stack(self) -> None:
        """Move to next entry in execution stack."""
        self._stack_index += 1

    def clear_execution_stack(self) -> None:
        """Empty execution stack and reset index."""
        self._execution_stack.clear()
        self._stack_index = 0

    def add_events(self, events: Sequence[schema.TurnEvent]) -> None:
        """Add events to the internal list."""
        self._events.extend(events)

    def add_event(self, event: schema.TurnEvent) -> None:
        """Add a single event to the internal list."""
        self._events.append(event)


class PhaseState(abc.ABC):
    """Abstract base for battle phase states."""

    def __init__(self, machine: BattleStateMachine) -> None:
        self.machine = machine

    @abc.abstractmethod
    def execute(self) -> None:
        """Execute phase logic."""
        ...


class ActionSortingState(PhaseState):
    """Phase I: Sort actions by priority + speed, build execution stack."""

    def execute(self) -> None:
        a = self.machine.battle.trainer_a.active_vibemon
        b = self.machine.battle.trainer_b.active_vibemon
        action_a = self.machine.battle.turn_history[-1].actions[0]
        action_b = self.machine.battle.turn_history[-1].actions[1]
        stack = resolve_turn_order(a, b, action_a, action_b, self.machine.rng)
        self.machine.set_execution_stack(stack)
        self.machine.transition(Phase.PRE_ACTION_CHECKS)


class PreActionChecksState(PhaseState):
    """Phase II.1: Can-Act check – status/volatile effects."""

    def execute(self) -> None:
        entry = self.machine.current_stack_entry
        if entry is None:
            self.machine.transition(Phase.END_OF_TURN)
            return

        attacker, defender, action = entry
        if action.action_type != types.ActionTypeT.MOVE or not attacker.moves:
            self.machine.advance_stack()
            self.machine.transition(Phase.PRE_ACTION_CHECKS)
            return

        result = check_pre_action(attacker, rng=self.machine.rng)
        self.machine.add_events(result.events)

        if not result.blocked:
            self.machine.transition(Phase.EXECUTE_STACK)
        else:
            self.machine.advance_stack()
            self.machine.transition(Phase.PRE_ACTION_CHECKS)


class ExecuteStackState(PhaseState):
    """Phase II.2–4: Execute move, hit check, damage, effects."""

    def execute(self) -> None:
        entry = self.machine.current_stack_entry
        if entry is None:
            self.machine.transition(Phase.END_OF_TURN)
            return

        attacker, defender, action = entry

        if action.action_type == types.ActionTypeT.MOVE and attacker.moves:
            move = find_move(attacker, action.value)
            move.pp_current -= 1
            events = execute_attack(attacker, defender, move, rng=self.machine.rng)
            self.machine.add_events(events)

            if defender.is_fainted:
                self.machine.add_event(
                    schema.TurnEvent(actor=defender.name, fainted=True, description=f"{defender.name} fainted!")
                )
                self.machine.clear_execution_stack()
                self.machine.transition(Phase.END_OF_TURN)
                return

        self.machine.advance_stack()
        if self.machine.current_stack_entry is not None:
            self.machine.transition(Phase.PRE_ACTION_CHECKS)
        else:
            self.machine.transition(Phase.END_OF_TURN)


class EndOfTurnState(PhaseState):
    """Phase III: End-of-turn maintenance – status damage, vol expiry."""

    def execute(self) -> None:
        a = self.machine.battle.trainer_a.active_vibemon
        b = self.machine.battle.trainer_b.active_vibemon

        for v in (a, b):
            if dmg := apply_status_damage(v):
                self.machine.add_event(
                    schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} takes status damage: {dmg}")
                )
                if v.is_fainted:
                    self.machine.add_event(schema.TurnEvent(actor=v.name, fainted=True))

        for v in sorted([a, b], key=effective_speed, reverse=True):
            self.machine.add_events(end_of_turn_maintenance(v))

        self.machine.transition(Phase.TURN_END)


class TurnEndState(PhaseState):
    """Phase: Increment turn number, check winner."""

    def execute(self) -> None:
        self.machine.battle.turn_number += 1
        winner = determine_winner(self.machine.battle)
        if not winner:
            a = self.machine.battle.trainer_a.active_vibemon
            b = self.machine.battle.trainer_b.active_vibemon
            if a.is_fainted and b.is_fainted:
                winner = self.machine.battle.trainer_b
        if winner:
            self.machine.battle.winner = winner
        else:
            self.machine.transition(Phase.ACTION_SORTING)


PHASE_STATE_MAP: dict[Phase, type[PhaseState]] = {
    Phase.ACTION_SORTING: ActionSortingState,
    Phase.PRE_ACTION_CHECKS: PreActionChecksState,
    Phase.EXECUTE_STACK: ExecuteStackState,
    Phase.END_OF_TURN: EndOfTurnState,
    Phase.TURN_END: TurnEndState,
}


def clamp_stage(stage: int) -> int:
    """Clamp stat stage to [-6, +6]."""
    return max(const.STAT_STAGE_MIN, min(const.STAT_STAGE_MAX, stage))


def _stage_multiplier(stage: int, base: int = 2) -> float:
    """Stat stage multiplier with configurable base (2 for combat stats, 3 for accuracy/evasion)."""
    stage = clamp_stage(stage)
    if stage >= 0:
        return (base + stage) / base
    return base / (base + abs(stage))


def stat_stage_multiplier(stage: int) -> float:
    """Combat stat stage multiplier from -6 to +6."""
    return _stage_multiplier(stage, base=2)


def _accuracy_modifier(accuracy_stage: int, evasion_stage: int) -> float:
    """Calculate accuracy modifier from stat stages per spec."""
    acc_mult = _stage_multiplier(accuracy_stage, base=const.STAT_ACCURACY_DIVISOR)
    eva_mult = _stage_multiplier(evasion_stage, base=const.STAT_ACCURACY_DIVISOR)
    return acc_mult / eva_mult


def effective_speed(v: schema.BattleVibemon) -> float:
    """Speed_Effective = Base x StatModifier per spec."""
    return v.speed * stat_stage_multiplier(v.stat_stages.speed)


def resolve_speed_tie(a_speed: float, b_speed: float, rng: random.Random) -> tuple[int, int]:
    """Resolve speed tie with random bit. Returns (slot_a, slot_b) order."""
    if a_speed == b_speed:
        bit = rng.randint(0, 1)
        return (1 - bit, bit)
    return (0, 1) if a_speed >= b_speed else (1, 0)


def _is_crit(crit_stage: int, move_crit_ratio: int, rng: random.Random) -> bool:
    """Roll for a critical hit using the Gen VI+ stage system.

    Stages stack additively (vibemon crit_stage + move crit_ratio) and index
    into a probability table: 1/24, 1/8, 1/2, guaranteed. This rewards
    investment (high-crit moves, Focus Energy) without making crits common
    at baseline (~4% at stage 0).
    """
    effective_stage = min(crit_stage + move_crit_ratio, 3)
    return rng.random() < const.CRIT_THRESHOLDS[effective_stage]


def calc_damage(
    attacker: schema.BattleVibemon,
    defender: schema.BattleVibemon,
    move: schema.BattleMove,
    rng: random.Random,
) -> tuple[int, bool]:
    """Calculate damage and determine if a critical hit occurred.

    Critical hits multiply final damage by 1.5x, but their real impact is
    ignoring unfavorable stat stages: the attacker's negative offensive stages
    and the defender's positive defensive stages are zeroed out. This prevents
    a heavily-debuffed attacker from being completely neutralized and gives
    crits strategic value beyond raw damage.
    """
    if move.category == types.MoveCategoryT.STATUS or move.power is None:
        return 0, False

    if move.category == types.MoveCategoryT.PHYSICAL:
        atk, def_ = attacker.attack, defender.defense
        atk_stage_field = "attack"
        def_stage_field = "defense"
    else:
        atk, def_ = attacker.sp_attack, defender.sp_defense
        atk_stage_field = "sp_attack"
        def_stage_field = "sp_defense"

    is_crit = _is_crit(attacker.crit_stage, move.crit_ratio, rng)

    if is_crit:
        atk_stage = stat_stage_multiplier(max(0, getattr(attacker.stat_stages, atk_stage_field)))
        def_stage = stat_stage_multiplier(min(0, getattr(defender.stat_stages, def_stage_field)))
        crit = const.CRITICAL_HIT_MULTIPLIER
    else:
        atk_stage = stat_stage_multiplier(getattr(attacker.stat_stages, atk_stage_field))
        def_stage = stat_stage_multiplier(getattr(defender.stat_stages, def_stage_field))
        crit = 1.0

    base = (2 * attacker.level / 5 + const.DAMAGE_BASE_ADDEND) * move.power * atk * atk_stage / (
        def_ * def_stage
    ) / const.DAMAGE_DIVISOR + const.DAMAGE_BASE_ADDEND
    stab = const.STAB_MULTIPLIER if move.type in attacker.elements else 1.0
    type_eff = element_chart.get_element_effectiveness(move.type, defender.elements)
    burn = (
        const.BURN_PHYSICAL_REDUCTION
        if (attacker.status == types.StatusConditionT.BURN and move.category == types.MoveCategoryT.PHYSICAL)
        else 1.0
    )
    damage_randomness = rng.uniform(const.DAMAGE_RANDOM_MIN, const.DAMAGE_RANDOM_MAX)

    damage = int(base * stab * type_eff * crit * burn * damage_randomness)
    return max(1, damage), is_crit


class PreActionResult(BaseModel):
    """Result of a pre-action check determining if a vibemon can act."""

    blocked: bool
    events: list[schema.TurnEvent] = pydantic.Field(default_factory=list)


def resolve_turn_order(
    a: schema.BattleVibemon,
    b: schema.BattleVibemon,
    action_a: schema.BattleAction,
    action_b: schema.BattleAction,
    rng: random.Random,
) -> list[StackEntry]:
    """Return (attacker, defender, action) tuples in resolution order.

    Priority brackets (+5 to -7) from spec. Higher priority moves first.
    Speed tie resolved via random bit.
    """
    if action_a.action_type == types.ActionTypeT.MOVE:
        move_a = find_move(a, action_a.value)
    else:
        move_a = None
    if action_b.action_type == types.ActionTypeT.MOVE:
        move_b = find_move(b, action_b.value)
    else:
        move_b = None

    prio_a = move_a.priority if move_a else 0
    prio_b = move_b.priority if move_b else 0

    if prio_a != prio_b:
        if prio_a > prio_b:
            return [(a, b, action_a), (b, a, action_b)]
        return [(b, a, action_b), (a, b, action_a)]

    order = resolve_speed_tie(effective_speed(a), effective_speed(b), rng)
    if order[0] == 0:
        return [(a, b, action_a), (b, a, action_b)]
    return [(b, a, action_b), (a, b, action_a)]


def find_move(vibemon: schema.BattleVibemon, move_name: str) -> schema.BattleMove:
    """Look up a move by name on a vibemon, raising ValueError if not found."""
    for m in vibemon.moves:
        if m.name == move_name:
            return m
    raise ValueError(f"{vibemon.name} has no move named {move_name!r}")


def check_pre_action(v: schema.BattleVibemon, *, rng: random.Random) -> PreActionResult:
    """Tick pre-action status/volatile effects per spec order.

    Spec: Faint → Sleep/Freeze → Flinch → Paralysis → Confusion.
    """
    if v.is_fainted:
        return PreActionResult(blocked=True)

    if v.status == types.StatusConditionT.SLEEP:
        v.sleep_turns_remaining -= 1
        if v.sleep_turns_remaining <= 0:
            v.status = types.StatusConditionT.NONE
            return PreActionResult(
                blocked=False,
                events=[schema.TurnEvent(actor=v.name, description=f"{v.name} woke up!")],
            )
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is asleep!")],
        )

    if v.status == types.StatusConditionT.FREEZE:
        if rng.random() < const.FREEZE_THAW_CHANCE:
            v.status = types.StatusConditionT.NONE
            return PreActionResult(
                blocked=False,
                events=[schema.TurnEvent(actor=v.name, description=f"{v.name} thawed out!")],
            )
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is frozen!")],
        )

    if v.is_flinched:
        v.is_flinched = False
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} flinched!")],
        )

    if v.status == types.StatusConditionT.PARALYSIS and rng.random() < const.PARALYSIS_FULLY_PARALYZED_CHANCE:
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is paralyzed and can't move!")],
        )

    if v.is_confused:
        if rng.random() < const.CONFUSION_SELF_HIT_CHANCE:
            dmg = v.max_hp // const.CONFUSION_SELF_HIT_DIVISOR
            v.current_hp = max(0, v.current_hp - dmg)
            return PreActionResult(
                blocked=True,
                events=[
                    schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} hurt itself in confusion!")
                ],
            )

    return PreActionResult(blocked=False)


def apply_move_effects(
    attacker: schema.BattleVibemon,
    defender: schema.BattleVibemon,
    move: schema.BattleMove,
    rng: random.Random,
) -> list[schema.TurnEvent]:
    """Roll for and apply secondary move effects (status infliction, stat changes)."""
    events: list[schema.TurnEvent] = []
    if not move.effect or rng.random() >= move.effect.chance:
        return events

    if move.effect.status_inflict and defender.status == types.StatusConditionT.NONE:
        defender.status = move.effect.status_inflict
        events.append(
            schema.TurnEvent(
                actor=attacker.name,
                status_change=defender.status,
                description=f"{defender.name} got {defender.status.value}!",
            )
        )

    for stat, change in move.effect.stat_changes.items():
        if hasattr(defender.stat_stages, stat):
            new_stage = clamp_stage(getattr(defender.stat_stages, stat) + change)
            setattr(defender.stat_stages, stat, new_stage)
            if change < 0:
                events.append(
                    schema.TurnEvent(
                        actor=attacker.name,
                        stat_stage_changes={stat: change},
                        description=f"{defender.name}'s {stat} fell!",
                    )
                )

    return events


def execute_attack(
    attacker: schema.BattleVibemon,
    defender: schema.BattleVibemon,
    move: schema.BattleMove,
    rng: random.Random,
) -> list[schema.TurnEvent]:
    """Accuracy roll with modifiers per spec, then damage/effects."""
    if move.accuracy is not None:
        acc_mod = _accuracy_modifier(attacker.stat_stages.accuracy, defender.stat_stages.evasion)
        final_accuracy = move.accuracy * acc_mod
        if rng.random() > final_accuracy:
            return [
                schema.TurnEvent(
                    actor=attacker.name,
                    missed=True,
                    move_used=move.name,
                    description=f"{attacker.name}'s {move.name} missed!",
                )
            ]

    damage, is_crit = calc_damage(attacker, defender, move, rng)
    events: list[schema.TurnEvent] = []

    if damage > 0:
        defender.current_hp = max(0, defender.current_hp - damage)
        type_eff = element_chart.get_element_effectiveness(move.type, defender.elements)
        eff_text = " Super effective!" if type_eff > 1 else " Not very effective..." if type_eff < 1 else ""
        crit_text = " Critical hit!" if is_crit else ""
        events.append(
            schema.TurnEvent(
                actor=attacker.name,
                move_used=move.name,
                hp_delta=-damage,
                description=f"{attacker.name} used {move.name}! {damage} damage.{crit_text}{eff_text}",
            )
        )
    else:
        events.append(
            schema.TurnEvent(
                actor=attacker.name,
                move_used=move.name,
                description=f"{attacker.name} used {move.name}!",
            )
        )

    events.extend(apply_move_effects(attacker, defender, move, rng))
    return events


def determine_winner(battle: schema.Battle) -> schema.BattleTrainer | None:
    """Return winning trainer if opponent's active vibemon fainted, else None."""
    if battle.trainer_a.active_vibemon.is_fainted:
        return battle.trainer_b
    if battle.trainer_b.active_vibemon.is_fainted:
        return battle.trainer_a
    return None


def apply_status_damage(v: schema.BattleVibemon) -> int:
    """Apply end-of-turn damage from burn, poison, or bad poison."""
    match v.status:
        case types.StatusConditionT.BURN:
            dmg = v.max_hp // const.BURN_DAMAGE_DIVISOR
        case types.StatusConditionT.POISON:
            dmg = v.max_hp // const.POISON_DAMAGE_DIVISOR
        case types.StatusConditionT.BAD_POISON:
            v.bad_poison_counter += 1
            dmg = v.max_hp * v.bad_poison_counter // const.BURN_DAMAGE_DIVISOR
        case _:
            return 0
    v.current_hp = max(0, v.current_hp - dmg)
    return dmg


def end_of_turn_maintenance(v: schema.BattleVibemon) -> list[schema.TurnEvent]:
    """End-of-turn status expiry — confusion, taunt, bound."""
    events: list[schema.TurnEvent] = []

    if v.is_confused:
        v.confusion_turns -= 1
        if v.confusion_turns <= 0:
            v.is_confused = False
            events.append(schema.TurnEvent(actor=v.name, description=f"{v.name} snapped out of confusion!"))

    if v.taunt_turns > 0:
        v.taunt_turns -= 1
        if v.taunt_turns <= 0:
            events.append(schema.TurnEvent(actor=v.name, description=f"{v.name}'s taunt wore off!"))

    if v.bound_turns > 0:
        v.bound_turns -= 1
        if v.bound_turns <= 0:
            events.append(schema.TurnEvent(actor=v.name, description=f"{v.name} is freed from bind!"))

    return events


class GameEngine:
    """Battle engine managing the turn-by-turn execution of a Pokémon-style battle."""

    def __init__(
        self,
        trainer_a: schema.BattleTrainer,
        trainer_b: schema.BattleTrainer,
        *,
        rng: random.Random | None = None,
    ) -> None:
        self._rng = rng or random.Random()
        self.battle = schema.Battle(
            trainer_a=trainer_a,
            trainer_b=trainer_b,
            turn_number=1,
            turn_history=[],
        )

    def submit(self, action_a: schema.BattleAction, action_b: schema.BattleAction) -> list[schema.TurnEvent]:
        """Process a turn with the given actions and return resulting events."""
        self.battle.turn_history.append(
            schema.TurnRecord(
                turn_number=self.battle.turn_number,
                actions=[action_a, action_b],
                events=[],
            )
        )

        machine = BattleStateMachine(self.battle, self._rng)

        while not self.battle.concluded:
            state_class = PHASE_STATE_MAP[machine.current_phase]
            state = state_class(machine)
            state.execute()

            if machine.current_phase == Phase.ACTION_SORTING:
                break

        events = machine.events

        self.battle.turn_history[-1].events = events

        return events
