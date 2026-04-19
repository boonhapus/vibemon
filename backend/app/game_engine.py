import random
import uuid
from collections.abc import Iterator

import attrs

from app import schema, types
from app.type_chart import get_type_effectiveness


CRIT_THRESHOLDS = [1 / 24, 1 / 8, 1 / 2, 1.0]


def _stat_stage_mod(stage: int) -> float:
    if stage >= 0:
        return 2 ** (stage / 2)
    return 2 / (2 ** abs(stage / 2))


def _is_crit(crit_stage: int, move_crit_ratio: int) -> bool:
    """Roll for a critical hit using the Gen VI+ stage system.

    Stages stack additively (vibemon crit_stage + move crit_ratio) and index
    into a probability table: 1/24, 1/8, 1/2, guaranteed. This rewards
    investment (high-crit moves, Focus Energy) without making crits common
    at baseline (~4% at stage 0).
    """
    effective_stage = min(crit_stage + move_crit_ratio, 3)
    return random.random() < CRIT_THRESHOLDS[effective_stage]


def calc_damage(
    attacker: schema.BattleVibemon, defender: schema.BattleVibemon, move: types.Move, turn: int
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

    is_crit = _is_crit(attacker.crit_stage, move.crit_ratio)

    if is_crit:
        atk_stage = _stat_stage_mod(max(0, getattr(attacker.stat_stages, atk_stage_field)))
        def_stage = _stat_stage_mod(min(0, getattr(defender.stat_stages, def_stage_field)))
        crit = 1.5
    else:
        atk_stage = _stat_stage_mod(getattr(attacker.stat_stages, atk_stage_field))
        def_stage = _stat_stage_mod(getattr(defender.stat_stages, def_stage_field))
        crit = 1.0

    base = (2 * attacker.level / 5 + 2) * move.power * atk * atk_stage / (def_ * def_stage) / 50 + 2
    stab = 1.5 if move.type in attacker.type_list else 1.0
    type_eff = get_type_effectiveness(move.type, defender.type_list)
    burn = (
        0.5
        if (attacker.status == types.StatusConditionT.BURN and move.category == types.MoveCategoryT.PHYSICAL)
        else 1.0
    )
    rng = 0.85 + (hash(str(turn)) % 16) / 100

    damage = int(base * stab * type_eff * crit * burn * rng)
    return max(1, damage), is_crit


@attrs.define(frozen=True)
class PreActionResult:
    blocked: bool
    events: list[schema.TurnEvent] = attrs.field(factory=list)


def resolve_turn_order(
    a: schema.BattleVibemon,
    b: schema.BattleVibemon,
    action_a: types.Action,
    action_b: types.Action,
) -> list[tuple[schema.BattleVibemon, schema.BattleVibemon, types.Action]]:
    """Return (attacker, defender, action) tuples in resolution order."""
    if a.speed >= b.speed:
        return [(a, b, action_a), (b, a, action_b)]
    return [(b, a, action_b), (a, b, action_a)]


def find_move(vibemon: schema.BattleVibemon, move_name: str) -> types.Move:
    for m in vibemon.moves:
        if m.name == move_name:
            return m
    raise ValueError(f"{vibemon.name} has no move named {move_name!r}")


def check_pre_action(v: schema.BattleVibemon) -> PreActionResult:
    """Tick pre-action status/volatile effects. Returns explicit blocked flag."""
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
        if random.random() < 0.2:
            v.status = types.StatusConditionT.NONE
            return PreActionResult(
                blocked=False,
                events=[schema.TurnEvent(actor=v.name, description=f"{v.name} thawed out!")],
            )
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is frozen!")],
        )

    if v.status == types.StatusConditionT.PARALYSIS and random.random() < 0.25:
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is paralyzed and can't move!")],
        )

    if v.is_flinched:
        v.is_flinched = False
        return PreActionResult(
            blocked=True,
            events=[schema.TurnEvent(actor=v.name, description=f"{v.name} flinched!")],
        )

    if v.is_confused:
        v.confusion_turns -= 1
        if v.confusion_turns <= 0:
            v.is_confused = False
            return PreActionResult(
                blocked=False,
                events=[schema.TurnEvent(actor=v.name, description=f"{v.name} is no longer confused!")],
            )
        if random.random() < 0.5:
            dmg = v.max_hp // 4
            v.current_hp = max(0, v.current_hp - dmg)
            return PreActionResult(
                blocked=True,
                events=[
                    schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} hurt itself in confusion!")
                ],
            )

    return PreActionResult(blocked=False)


def apply_move_effects(
    attacker: schema.BattleVibemon, defender: schema.BattleVibemon, move: types.Move
) -> list[schema.TurnEvent]:
    events: list[schema.TurnEvent] = []
    if not move.effect or random.random() >= move.effect.chance:
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
            new_stage = max(-6, min(6, getattr(defender.stat_stages, stat) + change))
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
    attacker: schema.BattleVibemon, defender: schema.BattleVibemon, move: types.Move, turn: int
) -> list[schema.TurnEvent]:
    """Accuracy roll, damage, effects. Assumes pre-action checks passed."""
    if move.accuracy and random.random() > move.accuracy:
        return [
            schema.TurnEvent(
                actor=attacker.name,
                missed=True,
                move_used=move.name,
                description=f"{attacker.name}'s {move.name} missed!",
            )
        ]

    damage, is_crit = calc_damage(attacker, defender, move, turn)
    defender.current_hp = max(0, defender.current_hp - damage)

    type_eff = get_type_effectiveness(move.type, defender.type_list)
    eff_text = " Super effective!" if type_eff > 1 else " Not very effective..." if type_eff < 1 else ""
    crit_text = " Critical hit!" if is_crit else ""

    events: list[schema.TurnEvent] = [
        schema.TurnEvent(
            actor=attacker.name,
            move_used=move.name,
            hp_delta=-damage,
            description=f"{attacker.name} used {move.name}! {damage} damage.{crit_text}{eff_text}",
        )
    ]
    events.extend(apply_move_effects(attacker, defender, move))
    return events


def determine_winner(battle: schema.BattleState) -> schema.Trainer | None:
    if battle.trainer_a.active_vibemon.is_fainted:
        return battle.trainer_b
    if battle.trainer_b.active_vibemon.is_fainted:
        return battle.trainer_a
    return None


def apply_status_damage(v: schema.BattleVibemon) -> int:
    if v.status == types.StatusConditionT.BURN:
        dmg = v.max_hp // 8
        v.current_hp = max(0, v.current_hp - dmg)
        return dmg
    elif v.status == types.StatusConditionT.POISON:
        dmg = v.max_hp // 8
        v.current_hp = max(0, v.current_hp - dmg)
        return dmg
    elif v.status == types.StatusConditionT.BAD_POISON:
        v.bad_poison_counter += 1
        dmg = v.max_hp * v.bad_poison_counter // 16
        v.current_hp = max(0, v.current_hp - dmg)
        return dmg
    return 0


class GameEngine:
    def __init__(self, trainer_a: schema.Trainer, trainer_b: schema.Trainer):
        self.battle = schema.BattleState(
            trainer_a=trainer_a,
            trainer_b=trainer_b,
            turn_number=1,
            turn_history=[],
        )

    def __iter__(self) -> Iterator[schema.BattleState]:
        while not self.battle.is_over:
            yield self.battle

    def submit(self, action_a: types.Action, action_b: types.Action) -> list[schema.TurnEvent]:
        events = self._execute_turn(action_a, action_b)
        self.battle.turn_history.append(
            schema.TurnRecord(
                turn_number=self.battle.turn_number,
                actions=[action_a, action_b],
                events=events,
            )
        )
        self.battle.winner = determine_winner(self.battle)
        if not self.battle.is_over:
            self.battle.turn_number += 1
        return events

    def _execute_turn(self, action_a: types.Action, action_b: types.Action) -> list[schema.TurnEvent]:
        events: list[schema.TurnEvent] = []
        a = self.battle.trainer_a.active_vibemon
        b = self.battle.trainer_b.active_vibemon

        for attacker, defender, action in resolve_turn_order(a, b, action_a, action_b):
            if action.action_type != types.ActionType.MOVE or not attacker.moves:
                continue

            pre = check_pre_action(attacker)
            events.extend(pre.events)

            if not pre.blocked:
                move = find_move(attacker, action.value)
                move.pp_current -= 1
                events.extend(execute_attack(attacker, defender, move, self.battle.turn_number))

            if defender.is_fainted:
                events.append(
                    schema.TurnEvent(actor=defender.name, fainted=True, description=f"{defender.name} fainted!")
                )
                return events

        for v in (a, b):
            if dmg := apply_status_damage(v):
                events.append(
                    schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} takes status damage: {dmg}")
                )
                if v.is_fainted:
                    events.append(schema.TurnEvent(actor=v.name, fainted=True))

        return events


if __name__ == "__main__":
    import random

    pikachu = schema.BattleVibemon(
        name="Pikachu",
        type_list=[types.VibemonT.ELECTRIC],
        base_hp=111,
        base_attack=55,
        base_defense=40,
        base_sp_attack=50,
        base_sp_defense=50,
        base_speed=90,
        moves=[
            types.Move(
                name="Thunderbolt",
                type=types.VibemonT.ELECTRIC,
                category=types.MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
                effect=types.MoveEffect(
                    status_inflict=types.StatusConditionT.PARALYSIS,
                    chance=0.10,
                ),
            ),
            types.Move(
                name="Quick Attack",
                type=types.VibemonT.NORMAL,
                category=types.MoveCategoryT.PHYSICAL,
                power=40,
                accuracy=1.0,
                pp=30,
                pp_current=30,
                priority=1,
                makes_contact=True,
            ),
            types.Move(
                name="Thunder Wave",
                type=types.VibemonT.ELECTRIC,
                category=types.MoveCategoryT.STATUS,
                accuracy=0.9,
                pp=20,
                pp_current=20,
                effect=types.MoveEffect(status_inflict=types.StatusConditionT.PARALYSIS, chance=1.0),
            ),
            types.Move(
                name="Iron Tail",
                type=types.VibemonT.STEEL,
                category=types.MoveCategoryT.PHYSICAL,
                power=100,
                accuracy=0.75,
                pp=15,
                pp_current=15,
                makes_contact=True,
                effect=types.MoveEffect(
                    stat_changes={"defense": -1},
                    target_self=False,
                    chance=0.30,
                ),
            ),
        ],
    )

    charizard = schema.BattleVibemon(
        name="Charizard",
        base_hp=148,
        base_attack=84,
        base_defense=78,
        base_sp_attack=109,
        base_sp_defense=85,
        base_speed=100,
        type_list=[types.VibemonT.FIRE, types.VibemonT.FLYING],
        moves=[
            types.Move(
                name="Flamethrower",
                type=types.VibemonT.FIRE,
                category=types.MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
                effect=types.MoveEffect(status_inflict=types.StatusConditionT.BURN, chance=0.10),
            ),
        ],
    )

    engine = GameEngine(
        trainer_a=schema.Trainer(id=uuid.uuid4(), name="Red", team=[pikachu]),
        trainer_b=schema.Trainer(id=uuid.uuid4(), name="Blue", team=[charizard]),
    )

    for battle_state in engine:
        action_a = types.Action(
            trainer_name=battle_state.trainer_a.id,
            action_type=types.ActionType.MOVE,
            value=random.choice(battle_state.trainer_a.active_vibemon.moves).name,
        )
        action_b = types.Action(
            trainer_name=battle_state.trainer_b.id,
            action_type=types.ActionType.MOVE,
            value=random.choice(battle_state.trainer_b.active_vibemon.moves).name,
        )

        engine.submit(action_a, action_b)

    assert engine.battle.is_over and engine.battle.winner is not None, "Battle is in an unresolved state."
    print(f"\n*** {engine.battle.winner.name} wins! ***")

    print(engine.battle.to_json())
