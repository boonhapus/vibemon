import random
import uuid

from app import schema, types


TYPE_CHART: dict[tuple[types.VibemonT, types.VibemonT], float] = {
    (types.VibemonT.NORMAL, types.VibemonT.ROCK): 0.5,
    (types.VibemonT.NORMAL, types.VibemonT.GHOST): 0.0,
    (types.VibemonT.NORMAL, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.FIRE, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.FIRE, types.VibemonT.WATER): 0.5,
    (types.VibemonT.FIRE, types.VibemonT.GRASS): 2.0,
    (types.VibemonT.FIRE, types.VibemonT.ICE): 2.0,
    (types.VibemonT.FIRE, types.VibemonT.BUG): 2.0,
    (types.VibemonT.FIRE, types.VibemonT.ROCK): 0.5,
    (types.VibemonT.FIRE, types.VibemonT.DRAGON): 0.5,
    (types.VibemonT.WATER, types.VibemonT.FIRE): 2.0,
    (types.VibemonT.WATER, types.VibemonT.WATER): 0.5,
    (types.VibemonT.WATER, types.VibemonT.GRASS): 0.5,
    (types.VibemonT.WATER, types.VibemonT.GROUND): 2.0,
    (types.VibemonT.WATER, types.VibemonT.ROCK): 2.0,
    (types.VibemonT.WATER, types.VibemonT.DRAGON): 0.5,
    (types.VibemonT.ELECTRIC, types.VibemonT.WATER): 2.0,
    (types.VibemonT.ELECTRIC, types.VibemonT.ELECTRIC): 0.5,
    (types.VibemonT.ELECTRIC, types.VibemonT.GRASS): 0.5,
    (types.VibemonT.ELECTRIC, types.VibemonT.GROUND): 0.0,
    (types.VibemonT.ELECTRIC, types.VibemonT.FLYING): 2.0,
    (types.VibemonT.ELECTRIC, types.VibemonT.DRAGON): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.WATER): 2.0,
    (types.VibemonT.GRASS, types.VibemonT.GRASS): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.POISON): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.GROUND): 2.0,
    (types.VibemonT.GRASS, types.VibemonT.FLYING): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.BUG): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.ROCK): 2.0,
    (types.VibemonT.GRASS, types.VibemonT.DRAGON): 0.5,
    (types.VibemonT.GRASS, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.ICE, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.ICE, types.VibemonT.WATER): 0.5,
    (types.VibemonT.ICE, types.VibemonT.GRASS): 2.0,
    (types.VibemonT.ICE, types.VibemonT.ICE): 0.5,
    (types.VibemonT.ICE, types.VibemonT.GROUND): 2.0,
    (types.VibemonT.ICE, types.VibemonT.FLYING): 2.0,
    (types.VibemonT.ICE, types.VibemonT.DRAGON): 2.0,
    (types.VibemonT.ICE, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.FIGHTING, types.VibemonT.NORMAL): 2.0,
    (types.VibemonT.FIGHTING, types.VibemonT.ICE): 2.0,
    (types.VibemonT.FIGHTING, types.VibemonT.POISON): 0.5,
    (types.VibemonT.FIGHTING, types.VibemonT.FLYING): 0.5,
    (types.VibemonT.FIGHTING, types.VibemonT.PSYCHIC): 0.5,
    (types.VibemonT.FIGHTING, types.VibemonT.BUG): 0.5,
    (types.VibemonT.FIGHTING, types.VibemonT.ROCK): 2.0,
    (types.VibemonT.FIGHTING, types.VibemonT.GHOST): 0.0,
    (types.VibemonT.FIGHTING, types.VibemonT.DARK): 2.0,
    (types.VibemonT.FIGHTING, types.VibemonT.STEEL): 2.0,
    (types.VibemonT.FIGHTING, types.VibemonT.FAIRY): 0.5,
    (types.VibemonT.POISON, types.VibemonT.GRASS): 2.0,
    (types.VibemonT.POISON, types.VibemonT.POISON): 0.5,
    (types.VibemonT.POISON, types.VibemonT.GROUND): 0.5,
    (types.VibemonT.POISON, types.VibemonT.ROCK): 0.5,
    (types.VibemonT.POISON, types.VibemonT.GHOST): 0.5,
    (types.VibemonT.POISON, types.VibemonT.STEEL): 0.0,
    (types.VibemonT.POISON, types.VibemonT.FAIRY): 2.0,
    (types.VibemonT.GROUND, types.VibemonT.FIRE): 2.0,
    (types.VibemonT.GROUND, types.VibemonT.ELECTRIC): 2.0,
    (types.VibemonT.GROUND, types.VibemonT.GRASS): 0.5,
    (types.VibemonT.GROUND, types.VibemonT.POISON): 2.0,
    (types.VibemonT.GROUND, types.VibemonT.FLYING): 0.0,
    (types.VibemonT.GROUND, types.VibemonT.BUG): 0.5,
    (types.VibemonT.GROUND, types.VibemonT.ROCK): 2.0,
    (types.VibemonT.GROUND, types.VibemonT.STEEL): 2.0,
    (types.VibemonT.FLYING, types.VibemonT.ELECTRIC): 0.5,
    (types.VibemonT.FLYING, types.VibemonT.GRASS): 2.0,
    (types.VibemonT.FLYING, types.VibemonT.FIGHTING): 2.0,
    (types.VibemonT.FLYING, types.VibemonT.BUG): 2.0,
    (types.VibemonT.FLYING, types.VibemonT.ROCK): 0.5,
    (types.VibemonT.FLYING, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.PSYCHIC, types.VibemonT.FIGHTING): 2.0,
    (types.VibemonT.PSYCHIC, types.VibemonT.POISON): 2.0,
    (types.VibemonT.PSYCHIC, types.VibemonT.PSYCHIC): 0.5,
    (types.VibemonT.PSYCHIC, types.VibemonT.DARK): 0.0,
    (types.VibemonT.PSYCHIC, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.BUG, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.BUG, types.VibemonT.GRASS): 2.0,
    (types.VibemonT.BUG, types.VibemonT.FIGHTING): 0.5,
    (types.VibemonT.BUG, types.VibemonT.POISON): 0.5,
    (types.VibemonT.BUG, types.VibemonT.FLYING): 0.5,
    (types.VibemonT.BUG, types.VibemonT.PSYCHIC): 2.0,
    (types.VibemonT.BUG, types.VibemonT.GHOST): 0.5,
    (types.VibemonT.BUG, types.VibemonT.DARK): 2.0,
    (types.VibemonT.BUG, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.BUG, types.VibemonT.FAIRY): 0.5,
    (types.VibemonT.ROCK, types.VibemonT.FIRE): 2.0,
    (types.VibemonT.ROCK, types.VibemonT.ICE): 2.0,
    (types.VibemonT.ROCK, types.VibemonT.FIGHTING): 0.5,
    (types.VibemonT.ROCK, types.VibemonT.GROUND): 0.5,
    (types.VibemonT.ROCK, types.VibemonT.FLYING): 2.0,
    (types.VibemonT.ROCK, types.VibemonT.BUG): 2.0,
    (types.VibemonT.ROCK, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.GHOST, types.VibemonT.NORMAL): 0.0,
    (types.VibemonT.GHOST, types.VibemonT.PSYCHIC): 2.0,
    (types.VibemonT.GHOST, types.VibemonT.GHOST): 2.0,
    (types.VibemonT.GHOST, types.VibemonT.DARK): 0.5,
    (types.VibemonT.DRAGON, types.VibemonT.DRAGON): 2.0,
    (types.VibemonT.DRAGON, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.DRAGON, types.VibemonT.FAIRY): 0.0,
    (types.VibemonT.DARK, types.VibemonT.PSYCHIC): 2.0,
    (types.VibemonT.DARK, types.VibemonT.GHOST): 2.0,
    (types.VibemonT.DARK, types.VibemonT.DARK): 0.5,
    (types.VibemonT.DARK, types.VibemonT.FAIRY): 0.5,
    (types.VibemonT.STEEL, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.STEEL, types.VibemonT.WATER): 0.5,
    (types.VibemonT.STEEL, types.VibemonT.ELECTRIC): 0.5,
    (types.VibemonT.STEEL, types.VibemonT.ICE): 2.0,
    (types.VibemonT.STEEL, types.VibemonT.ROCK): 2.0,
    (types.VibemonT.STEEL, types.VibemonT.STEEL): 0.5,
    (types.VibemonT.STEEL, types.VibemonT.FAIRY): 2.0,
    (types.VibemonT.FAIRY, types.VibemonT.FIRE): 0.5,
    (types.VibemonT.FAIRY, types.VibemonT.FIGHTING): 2.0,
    (types.VibemonT.FAIRY, types.VibemonT.POISON): 0.5,
    (types.VibemonT.FAIRY, types.VibemonT.DRAGON): 2.0,
    (types.VibemonT.FAIRY, types.VibemonT.DARK): 2.0,
    (types.VibemonT.FAIRY, types.VibemonT.STEEL): 0.5,
}


def get_type_effectiveness(attack_type: types.VibemonT, defend_types: list[types.VibemonT]) -> float:
    for dtype in defend_types:
        mod = TYPE_CHART.get((attack_type, dtype), 1.0)
        if mod != 1.0:
            return mod
    return 1.0


def _stat_stage_mod(stage: int) -> float:
    if stage >= 0:
        return 2 ** (stage / 2)
    return 2 / (2 ** abs(stage / 2))


def calc_damage(attacker: schema.Vibemon, defender: schema.Vibemon, move: types.Move, turn: int) -> int:
    if move.category == types.MoveCategoryT.STATUS or move.power is None:
        return 0

    if move.category == types.MoveCategoryT.PHYSICAL:
        atk, def_ = attacker.attack, defender.defense
        def_stage_field = "defense"
    else:
        atk, def_ = attacker.sp_attack, defender.sp_defense
        def_stage_field = "sp_defense"

    atk_stage = _stat_stage_mod(attacker.stat_stages.attack)
    def_stage = _stat_stage_mod(getattr(defender.stat_stages, def_stage_field))

    base = (2 * attacker.level / 5 + 2) * move.power * atk * atk_stage / (def_ * def_stage) / 50 + 2
    stab = 1.5 if move.type in attacker.type_list else 1.0
    type_eff = get_type_effectiveness(move.type, defender.type_list)
    crit = 1.5
    burn = (
        0.5
        if (attacker.status == types.StatusConditionT.BURN and move.category == types.MoveCategoryT.PHYSICAL)
        else 1.0
    )
    rng = 0.85 + (hash(str(turn)) % 16) / 100

    damage = int(base * stab * type_eff * crit * burn * rng)
    return max(1, damage)


def apply_status_damage(v: schema.Vibemon) -> int:
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

    def run(self) -> dict:
        while not self.battle.is_over:
            events = self._execute_turn()
            self.battle.turn_history.append(schema.TurnRecord(turn_number=self.battle.turn_number, events=events))

            if self._check_winner():
                break
            self.battle.turn_number += 1

        return self._to_json()

    def _execute_turn(self) -> list[schema.TurnEvent]:
        events: list[schema.TurnEvent] = []
        a = self.battle.trainer_a.active_vibemon
        b = self.battle.trainer_b.active_vibemon

        order = (
            [self.battle.trainer_a, self.battle.trainer_b]
            if a.speed >= b.speed
            else [self.battle.trainer_b, self.battle.trainer_a]
        )

        for trainer in order:
            attacker = trainer.active_vibemon
            defender = (
                self.battle.trainer_b.active_vibemon
                if trainer == self.battle.trainer_a
                else self.battle.trainer_a.active_vibemon
            )

            ev = self._execute_attack(attacker, defender)
            if ev:
                events.extend(ev)

            if defender.is_fainted:
                events.append(schema.TurnEvent(actor=defender.name, fainted=True, description=f"{defender.name} fainted!"))
                return events

        for v in [a, b]:
            dmg = apply_status_damage(v)
            if dmg > 0:
                events.append(
                    schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} takes status damage: {dmg}")
                )
                if v.is_fainted:
                    events.append(schema.TurnEvent(actor=v.name, fainted=True))

        return events

    def _execute_attack(self, attacker: schema.Vibemon, defender: schema.Vibemon) -> list[schema.TurnEvent]:
        events: list[schema.TurnEvent] = []

        if not attacker.moves:
            return events

        status_ev = self._handle_status(attacker)
        if status_ev:
            events.append(status_ev)
            return events

        move = attacker.moves[0]
        move.pp_current -= 1

        if move.accuracy and random.random() > move.accuracy:
            events.append(
                schema.TurnEvent(
                    actor=attacker.name,
                    missed=True,
                    move_used=move.name,
                    description=f"{attacker.name}'s {move.name} missed!",
                )
            )
            return events

        damage = calc_damage(attacker, defender, move, self.battle.turn_number)
        defender.current_hp = max(0, defender.current_hp - damage)

        type_eff = get_type_effectiveness(move.type, defender.type_list)
        eff_text = " super effective!" if type_eff > 1 else " not very effective..." if type_eff < 1 else ""

        events.append(
            schema.TurnEvent(
                actor=attacker.name,
                move_used=move.name,
                hp_delta=-damage,
                description=f"{attacker.name} used {move.name}! {damage} damage{eff_text}",
            )
        )

        if move.effect and random.random() < move.effect.chance:
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
                    setattr(defender.stat_stages, stat, max(-6, min(6, getattr(defender.stat_stages, stat) + change)))
                    if change < 0:
                        events.append(
                            schema.TurnEvent(
                                actor=attacker.name,
                                stat_stage_changes={stat: change},
                                description=f"{defender.name}'s {stat} fell!",
                            )
                        )

        return events

    def _handle_status(self, v: schema.Vibemon) -> schema.TurnEvent | None:
        if v.status == types.StatusConditionT.SLEEP:
            v.sleep_turns_remaining -= 1
            if v.sleep_turns_remaining <= 0:
                v.status = types.StatusConditionT.NONE
                return schema.TurnEvent(actor=v.name, description=f"{v.name} woke up!")
            return schema.TurnEvent(actor=v.name, description=f"{v.name} is asleep!")

        if v.status == types.StatusConditionT.FREEZE:
            if random.random() < 0.2:
                v.status = types.StatusConditionT.NONE
                return schema.TurnEvent(actor=v.name, description=f"{v.name} thawed out!")
            return schema.TurnEvent(actor=v.name, description=f"{v.name} is frozen!")

        if v.status == types.StatusConditionT.PARALYSIS:
            if random.random() < 0.25:
                return schema.TurnEvent(actor=v.name, description=f"{v.name} is paralyzed and can't move!")

        if v.is_flinched:
            v.is_flinched = False
            return schema.TurnEvent(actor=v.name, description=f"{v.name} flinched!")

        if v.is_confused:
            v.confusion_turns -= 1
            if v.confusion_turns <= 0:
                v.is_confused = False
                return schema.TurnEvent(actor=v.name, description=f"{v.name} is no longer confused!")
            else:
                if random.random() < 0.5:
                    dmg = v.max_hp // 4
                    v.current_hp = max(0, v.current_hp - dmg)
                    return schema.TurnEvent(actor=v.name, hp_delta=-dmg, description=f"{v.name} hurt itself in confusion!")

        return None

    def _check_winner(self) -> bool:
        a = self.battle.trainer_a.active_vibemon
        b = self.battle.trainer_b.active_vibemon

        if a.is_fainted:
            self.battle.winner = self.battle.trainer_b.id
            print(f"\n*** {self.battle.trainer_b.name} wins! ***")
            return True
        if b.is_fainted:
            self.battle.winner = self.battle.trainer_a.id
            print(f"\n*** {self.battle.trainer_a.name} wins! ***")
            return True
        return False

    def _to_json(self) -> dict:
        return {
            "schema.trainer_a": self.battle.trainer_a.name,
            "schema.trainer_b": self.battle.trainer_b.name,
            "winner": str(self.battle.winner),
            "turns": len(self.battle.turn_history),
            "history": [
                {
                    "turn": tr.turn_number,
                    "events": [
                        {
                            "actor": e.actor,
                            "description": e.description,
                            "hp_delta": e.hp_delta,
                            "status_change": e.status_change.value if e.status_change else None,
                            "move_used": e.move_used,
                            "missed": e.missed,
                            "fainted": e.fainted,
                        }
                        for e in tr.events
                    ],
                }
                for tr in self.battle.turn_history
            ],
        }


def run_battle(
    name_a: str,
    vibemon_a: schema.Vibemon,
    name_b: str,
    vibemon_b: schema.Vibemon,
) -> dict:
    trainer_a = schema.Trainer(id=uuid.uuid4(), name=name_a, team=[vibemon_a])
    trainer_b = schema.Trainer(id=uuid.uuid4(), name=name_b, team=[vibemon_b])

    engine = GameEngine(trainer_a, trainer_b)
    return engine.run()


if __name__ == "__main__":
    import json

    pikachu = schema.Vibemon(
        name="Pikachu",
        type_list=[types.VibemonT.ELECTRIC],
        max_hp=111,
        attack=55,
        defense=40,
        sp_attack=50,
        sp_defense=50,
        speed=90,
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

    charizard = schema.Vibemon(
        name="Charizard",
        type_list=[types.VibemonT.FIRE, types.VibemonT.FLYING],
        max_hp=148,
        attack=84,
        defense=78,
        sp_attack=109,
        sp_defense=85,
        speed=100,
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

    result = run_battle("Ash", pikachu, "Gary", charizard)
    print(json.dumps(result, indent=2))
