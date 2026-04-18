from typing import Annotated, Self
import attrs
import cattrs
import enum
import uuid


type TrainerId = Annotated[uuid.UUID, "backend trainer identifier"]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VibemonT(str, enum.Enum):
    NORMAL = "normal"
    FIRE = "fire"
    WATER = "water"
    ELECTRIC = "electric"
    GRASS = "grass"
    ICE = "ice"
    FIGHTING = "fighting"
    POISON = "poison"
    GROUND = "ground"
    FLYING = "flying"
    PSYCHIC = "psychic"
    BUG = "bug"
    ROCK = "rock"
    GHOST = "ghost"
    DRAGON = "dragon"
    DARK = "dark"
    STEEL = "steel"
    FAIRY = "fairy"


class StatusConditionT(str, enum.Enum):
    NONE = "none"
    BURN = "burn"  # -1/8 max HP per turn; halves physical Attack
    POISON = "poison"  # -1/8 max HP per turn
    BAD_POISON = "bad_poison"  # damage scales up each turn
    PARALYSIS = "paralysis"  # 25% chance to skip turn; halves Speed
    SLEEP = "sleep"  # skips turns; wears off after 1-3 turns
    FREEZE = "freeze"  # skips turns; 20% thaw chance per turn
    FAINTED = "fainted"


class MoveCategoryT(str, enum.Enum):
    PHYSICAL = "physical"  # uses Attack / Defense
    SPECIAL = "special"  # uses Sp.Atk / Sp.Def
    STATUS = "status"  # no direct damage


class MoveTargetT(str, enum.Enum):
    SELF = "self"
    SINGLE = "single"
    ALL_OPPONENTS = "all_opponents"
    ALL_ADJACENT = "all_adjacent"


class WeatherT(str, enum.Enum):
    CLEAR = "clear"
    SUN = "sun"
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
    HEAVY_RAIN = "heavy_rain"
    EXTREME_SUN = "extreme_sun"
    STRONG_WINDS = "strong_winds"


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@attrs.define
class BaseStats:
    """The six permanent base stats of a species."""

    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int


@attrs.define
class StatStages:
    """
    In-battle stat stage modifiers (-6 to +6).

    Accuracy and evasion are also tracked here.
    """

    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


# ---------------------------------------------------------------------------
# Move
# ---------------------------------------------------------------------------


@attrs.define
class MoveEffect:
    """
    A secondary effect a move can have beyond direct damage.

    Examples: inflict burn (30%), lower target's Defense by 1 stage.
    """

    status_inflict: StatusConditionT | None = None
    # Positive = boost, negative = drop; applied to user if target_self=True
    stat_changes: dict[str, int] = attrs.field(factory=dict)
    target_self: bool = False
    chance: float = 1.0


@attrs.define
class Move:
    """A single move a Vibemon can know."""

    name: str
    type: VibemonT
    category: MoveCategoryT
    power: int | None = None  # None for status moves
    accuracy: float | None = 1.0  # None = always hits
    pp: int = 10
    pp_current: int = 10
    priority: int = 0  # higher goes first
    effect: MoveEffect | None = None
    makes_contact: bool = False
    # e.g. "self", "single", "all_opponents", "all_adjacent"
    target: MoveTargetT = MoveTargetT.SINGLE


# ---------------------------------------------------------------------------
# Vibemon
# ---------------------------------------------------------------------------


@attrs.define
class Vibemon:
    """
    A fully realised Vibemon — species data, learnt moves, and the volatile state that changes during battle.
    """

    # DEV NOTE: should we have a vibemon and a vibemon-in-battle ?

    # Identity
    name: str
    level: int = 50
    types: list[VibemonT] = []

    # Permanent stats (calculated from base stats + EVs/IVs/nature)
    max_hp: int = 100
    attack: int = 50
    defense: int = 50
    sp_attack: int = 50
    sp_defense: int = 50
    speed: int = 50

    # Battle state
    current_hp: int = 100
    status: StatusConditionT = StatusConditionT.NONE
    stat_stages: StatStages = attrs.field(factory=StatStages)
    moves: list[Move] = attrs.field(factory=list)

    # Volatile flags (reset when switched out)
    is_flinched: bool = False
    is_confused: bool = False
    confusion_turns: int = 0
    bad_poison_counter: int = 0  # scales toxic damage
    sleep_turns_remaining: int = 0
    is_seeded: bool = False  # Leech Seed

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0


# ---------------------------------------------------------------------------
# Trainer / Team
# ---------------------------------------------------------------------------


@attrs.define
class Trainer:
    """One side of a battle — a player or NPC with a team of Vibemon."""

    id: TrainerId
    name: str
    team: list[Vibemon] = attrs.field(factory=list)
    active_index: int = 0

    @property
    def active_vibemon(self) -> Vibemon:
        return self.team[self.active_index]

    @property
    def has_vibemon_remaining(self) -> bool:
        return any(not p.is_fainted for p in self.team)


# ---------------------------------------------------------------------------
# Action (what happens on a turn)
# ---------------------------------------------------------------------------


class ActionType(str, enum.Enum):
    MOVE = "move"
    SWITCH = "switch"
    ITEM = "item"
    RUN = "run"


@attrs.define
class Action:
    """The choice a trainer makes for their turn."""

    trainer_name: TrainerId
    action_type: ActionType
    # For MOVE: index into active Vibemon's move list (0-3)
    # For SWITCH: index into trainer's team
    # For ITEM: item name string
    value: str  # use str for indices too


# ---------------------------------------------------------------------------
# Turn Log
# ---------------------------------------------------------------------------


@attrs.define
class TurnEvent:
    """A single atomic event that occurred during a turn (for replay / logging)."""

    actor: Annotated[str, "Vibemon.name"]
    description: str | None = None
    hp_delta: int | None = None  # negative = damage, positive = heal
    status_change: StatusConditionT | None = None  # new status applied
    stat_stage_changes: dict[str, int] = attrs.field(factory=dict)  # e.g. {"attack": -1}
    move_used: str | None = None  # move name if applicable
    missed: bool = False
    fainted: bool = False


@attrs.define
class TurnRecord:
    """All events that happened in a single turn."""

    turn_number: int
    actions: list[Action] = attrs.field(factory=list)
    events: list[TurnEvent] = attrs.field(factory=list)


# ---------------------------------------------------------------------------
# Battle State (root object)
# ---------------------------------------------------------------------------


@attrs.define
class BattleState:
    """The complete, serialisable snapshot of a Vibemon battle."""

    trainer_a: Trainer
    trainer_b: Trainer
    turn_number: int = 1
    turn_history: list[TurnRecord] = attrs.field(factory=list)
    winner: TrainerId | None = None

    @property
    def is_over(self) -> bool:
        return self.winner is not None


# ---------------------------------------------------------------------------
# Cattrs converter
# ---------------------------------------------------------------------------

converter = cattrs.Converter()

# Teach cattrs how to handle str-valued Enums
for enum_cls in [VibemonT, StatusConditionT, MoveCategoryT, WeatherT, ActionType]:
    converter.register_structure_hook(enum_cls, lambda v, t: t(v))
    converter.register_unstructure_hook(enum_cls, lambda v: v.value)


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    pikachu = Vibemon(
        name="Pikachu",
        level=50,
        types=[VibemonT.ELECTRIC],
        max_hp=111,
        current_hp=111,
        attack=55,
        defense=40,
        sp_attack=50,
        sp_defense=50,
        speed=90,
        moves=[
            Move(
                name="Thunderbolt",
                type=VibemonT.ELECTRIC,
                category=MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
                effect=MoveEffect(
                    status_inflict=StatusConditionT.PARALYSIS,
                    chance=0.10,
                ),
            ),
            Move(
                name="Quick Attack",
                type=VibemonT.NORMAL,
                category=MoveCategoryT.PHYSICAL,
                power=40,
                accuracy=1.0,
                pp=30,
                pp_current=30,
                priority=1,
                makes_contact=True,
            ),
            Move(
                name="Thunder Wave",
                type=VibemonT.ELECTRIC,
                category=MoveCategoryT.STATUS,
                accuracy=0.9,
                pp=20,
                pp_current=20,
                effect=MoveEffect(status_inflict=StatusConditionT.PARALYSIS, chance=1.0),
            ),
            Move(
                name="Iron Tail",
                type=VibemonT.STEEL,
                category=MoveCategoryT.PHYSICAL,
                power=100,
                accuracy=0.75,
                pp=15,
                pp_current=15,
                makes_contact=True,
                effect=MoveEffect(
                    stat_changes={"defense": -1},
                    target_self=False,
                    chance=0.30,
                ),
            ),
        ],
    )

    charizard = Vibemon(
        name="Charizard",
        level=50,
        types=[VibemonT.FIRE, VibemonT.FLYING],
        max_hp=148,
        current_hp=148,
        attack=84,
        defense=78,
        sp_attack=109,
        sp_defense=85,
        speed=100,
        moves=[
            Move(
                name="Flamethrower",
                type=VibemonT.FIRE,
                category=MoveCategoryT.SPECIAL,
                power=90,
                accuracy=1.0,
                pp=15,
                pp_current=15,
                effect=MoveEffect(status_inflict=StatusConditionT.BURN, chance=0.10),
            ),
        ],
    )

    battle = BattleState(
        trainer_a=Trainer(id=uuid.UUID(), name="Ash", team=[pikachu]),
        trainer_b=Trainer(id=uuid.UUID(), name="Gary", team=[charizard]),
        turn_number=1,
    )

    def type_modifier(attacker: Vibemon, defender: Vibemon, move: Move) -> float:
        type_chart = {
            (VibemonT.NORMAL, VibemonT.ROCK): 0.5,
            (VibemonT.NORMAL, VibemonT.GHOST): 0.0,
            (VibemonT.NORMAL, VibemonT.STEEL): 0.5,
            (VibemonT.FIRE, VibemonT.FIRE): 0.5,
            (VibemonT.FIRE, VibemonT.WATER): 0.5,
            (VibemonT.FIRE, VibemonT.GRASS): 2.0,
            (VibemonT.FIRE, VibemonT.ICE): 2.0,
            (VibemonT.FIRE, VibemonT.BUG): 2.0,
            (VibemonT.FIRE, VibemonT.ROCK): 0.5,
            (VibemonT.FIRE, VibemonT.DRAGON): 0.5,
            (VibemonT.WATER, VibemonT.FIRE): 2.0,
            (VibemonT.WATER, VibemonT.WATER): 0.5,
            (VibemonT.WATER, VibemonT.GRASS): 0.5,
            (VibemonT.WATER, VibemonT.GROUND): 2.0,
            (VibemonT.WATER, VibemonT.ROCK): 2.0,
            (VibemonT.WATER, VibemonT.DRAGON): 0.5,
            (VibemonT.ELECTRIC, VibemonT.WATER): 2.0,
            (VibemonT.ELECTRIC, VibemonT.ELECTRIC): 0.5,
            (VibemonT.ELECTRIC, VibemonT.GRASS): 0.5,
            (VibemonT.ELECTRIC, VibemonT.GROUND): 0.0,
            (VibemonT.ELECTRIC, VibemonT.FLYING): 2.0,
            (VibemonT.ELECTRIC, VibemonT.DRAGON): 0.5,
            (VibemonT.GRASS, VibemonT.FIRE): 0.5,
            (VibemonT.GRASS, VibemonT.WATER): 2.0,
            (VibemonT.GRASS, VibemonT.GRASS): 0.5,
            (VibemonT.GRASS, VibemonT.POISON): 0.5,
            (VibemonT.GRASS, VibemonT.GROUND): 2.0,
            (VibemonT.GRASS, VibemonT.FLYING): 0.5,
            (VibemonT.GRASS, VibemonT.BUG): 0.5,
            (VibemonT.GRASS, VibemonT.ROCK): 2.0,
            (VibemonT.GRASS, VibemonT.DRAGON): 0.5,
            (VibemonT.GRASS, VibemonT.STEEL): 0.5,
            (VibemonT.ICE, VibemonT.FIRE): 0.5,
            (VibemonT.ICE, VibemonT.WATER): 0.5,
            (VibemonT.ICE, VibemonT.GRASS): 2.0,
            (VibemonT.ICE, VibemonT.ICE): 0.5,
            (VibemonT.ICE, VibemonT.GROUND): 2.0,
            (VibemonT.ICE, VibemonT.FLYING): 2.0,
            (VibemonT.ICE, VibemonT.DRAGON): 2.0,
            (VibemonT.ICE, VibemonT.STEEL): 0.5,
            (VibemonT.FIGHTING, VibemonT.NORMAL): 2.0,
            (VibemonT.FIGHTING, VibemonT.ICE): 2.0,
            (VibemonT.FIGHTING, VibemonT.POISON): 0.5,
            (VibemonT.FIGHTING, VibemonT.FLYING): 0.5,
            (VibemonT.FIGHTING, VibemonT.PSYCHIC): 0.5,
            (VibemonT.FIGHTING, VibemonT.BUG): 0.5,
            (VibemonT.FIGHTING, VibemonT.ROCK): 2.0,
            (VibemonT.FIGHTING, VibemonT.GHOST): 0.0,
            (VibemonT.FIGHTING, VibemonT.DARK): 2.0,
            (VibemonT.FIGHTING, VibemonT.STEEL): 2.0,
            (VibemonT.FIGHTING, VibemonT.FAIRY): 0.5,
            (VibemonT.POISON, VibemonT.GRASS): 2.0,
            (VibemonT.POISON, VibemonT.POISON): 0.5,
            (VibemonT.POISON, VibemonT.GROUND): 0.5,
            (VibemonT.POISON, VibemonT.ROCK): 0.5,
            (VibemonT.POISON, VibemonT.GHOST): 0.5,
            (VibemonT.POISON, VibemonT.STEEL): 0.0,
            (VibemonT.POISON, VibemonT.FAIRY): 2.0,
            (VibemonT.GROUND, VibemonT.FIRE): 2.0,
            (VibemonT.GROUND, VibemonT.ELECTRIC): 2.0,
            (VibemonT.GROUND, VibemonT.GRASS): 0.5,
            (VibemonT.GROUND, VibemonT.POISON): 2.0,
            (VibemonT.GROUND, VibemonT.FLYING): 0.0,
            (VibemonT.GROUND, VibemonT.BUG): 0.5,
            (VibemonT.GROUND, VibemonT.ROCK): 2.0,
            (VibemonT.GROUND, VibemonT.STEEL): 2.0,
            (VibemonT.FLYING, VibemonT.ELECTRIC): 0.5,
            (VibemonT.FLYING, VibemonT.GRASS): 2.0,
            (VibemonT.FLYING, VibemonT.FIGHTING): 2.0,
            (VibemonT.FLYING, VibemonT.BUG): 2.0,
            (VibemonT.FLYING, VibemonT.ROCK): 0.5,
            (VibemonT.FLYING, VibemonT.STEEL): 0.5,
            (VibemonT.PSYCHIC, VibemonT.FIGHTING): 2.0,
            (VibemonT.PSYCHIC, VibemonT.POISON): 2.0,
            (VibemonT.PSYCHIC, VibemonT.PSYCHIC): 0.5,
            (VibemonT.PSYCHIC, VibemonT.DARK): 0.0,
            (VibemonT.PSYCHIC, VibemonT.STEEL): 0.5,
            (VibemonT.BUG, VibemonT.FIRE): 0.5,
            (VibemonT.BUG, VibemonT.GRASS): 2.0,
            (VibemonT.BUG, VibemonT.FIGHTING): 0.5,
            (VibemonT.BUG, VibemonT.POISON): 0.5,
            (VibemonT.BUG, VibemonT.FLYING): 0.5,
            (VibemonT.BUG, VibemonT.PSYCHIC): 2.0,
            (VibemonT.BUG, VibemonT.GHOST): 0.5,
            (VibemonT.BUG, VibemonT.DARK): 2.0,
            (VibemonT.BUG, VibemonT.STEEL): 0.5,
            (VibemonT.BUG, VibemonT.FAIRY): 0.5,
            (VibemonT.ROCK, VibemonT.FIRE): 2.0,
            (VibemonT.ROCK, VibemonT.ICE): 2.0,
            (VibemonT.ROCK, VibemonT.FIGHTING): 0.5,
            (VibemonT.ROCK, VibemonT.GROUND): 0.5,
            (VibemonT.ROCK, VibemonT.FLYING): 2.0,
            (VibemonT.ROCK, VibemonT.BUG): 2.0,
            (VibemonT.ROCK, VibemonT.STEEL): 0.5,
            (VibemonT.GHOST, VibemonT.NORMAL): 0.0,
            (VibemonT.GHOST, VibemonT.PSYCHIC): 2.0,
            (VibemonT.GHOST, VibemonT.GHOST): 2.0,
            (VibemonT.GHOST, VibemonT.DARK): 0.5,
            (VibemonT.DRAGON, VibemonT.DRAGON): 2.0,
            (VibemonT.DRAGON, VibemonT.STEEL): 0.5,
            (VibemonT.DRAGON, VibemonT.FAIRY): 0.0,
            (VibemonT.DARK, VibemonT.PSYCHIC): 2.0,
            (VibemonT.DARK, VibemonT.GHOST): 2.0,
            (VibemonT.DARK, VibemonT.DARK): 0.5,
            (VibemonT.DARK, VibemonT.FAIRY): 0.5,
            (VibemonT.STEEL, VibemonT.FIRE): 0.5,
            (VibemonT.STEEL, VibemonT.WATER): 0.5,
            (VibemonT.STEEL, VibemonT.ELECTRIC): 0.5,
            (VibemonT.STEEL, VibemonT.ICE): 2.0,
            (VibemonT.STEEL, VibemonT.ROCK): 2.0,
            (VibemonT.STEEL, VibemonT.STEEL): 0.5,
            (VibemonT.STEEL, VibemonT.FAIRY): 2.0,
            (VibemonT.FAIRY, VibemonT.FIRE): 0.5,
            (VibemonT.FAIRY, VibemonT.FIGHTING): 2.0,
            (VibemonT.FAIRY, VibemonT.POISON): 0.5,
            (VibemonT.FAIRY, VibemonT.DRAGON): 2.0,
            (VibemonT.FAIRY, VibemonT.DARK): 2.0,
            (VibemonT.FAIRY, VibemonT.STEEL): 0.5,
        }
        mtype = move.type
        for dtype in defender.types:
            mod = type_chart.get((mtype, dtype), 1.0)
            if mod != 1.0:
                return mod
        return 1.0

    def calc_damage(attacker: Vibemon, defender: Vibemon, move: Move) -> int:
        if move.category == MoveCategoryT.STATUS or move.power is None:
            return 0
        if move.category == MoveCategoryT.PHYSICAL:
            atk, def_ = attacker.attack, defender.defense
        else:
            atk, def_ = attacker.sp_attack, defender.sp_defense
        atk_stage = (
            2 ** (attacker.stat_stages.attack / 2)
            if attacker.stat_stages.attack >= 0
            else 2 / (2 ** abs(attacker.stat_stages.attack / 2))
        )
        def_stage = (
            2 ** (defender.stat_stages.defense / 2)
            if defender.stat_stages.defense >= 0
            else 2 / (2 ** abs(defender.stat_stages.defense / 2))
        )
        if move.category == MoveCategoryT.PHYSICAL:
            def_stage = (
                2 ** (defender.stat_stages.defense / 2)
                if defender.stat_stages.defense >= 0
                else 2 / (2 ** abs(defender.stat_stages.defense / 2))
            )
        else:
            def_stage = (
                2 ** (defender.stat_stages.sp_defense / 2)
                if defender.stat_stages.sp_defense >= 0
                else 2 / (2 ** abs(defender.stat_stages.sp_defense / 2))
            )
        base = (2 * attacker.level / 5 + 2) * move.power * atk * atk_stage / (def_ * def_stage) / 50 + 2
        stab = 1.5 if move.type in attacker.types else 1.0
        type_eff = type_modifier(attacker, defender, move)
        crit = 1.5
        burn = 0.5 if (attacker.status == StatusConditionT.BURN and move.category == MoveCategoryT.PHYSICAL) else 1.0
        rng = 0.85 + (hash(str(battle.turn_number)) % 16) / 100
        damage = int(base * stab * type_eff * crit * burn * rng)
        return max(1, damage)

    def apply_status_damage(v: Vibemon) -> int:
        if v.status == StatusConditionT.BURN:
            dmg = v.max_hp // 8
            v.current_hp = max(0, v.current_hp - dmg)
            return dmg
        elif v.status == StatusConditionT.POISON:
            dmg = v.max_hp // 8
            v.current_hp = max(0, v.current_hp - dmg)
            return dmg
        elif v.status == StatusConditionT.BAD_POISON:
            v.bad_poison_counter += 1
            dmg = v.max_hp * v.bad_poison_counter // 16
            v.current_hp = max(0, v.current_hp - dmg)
            return dmg
        return 0

    def will_faint(hp: int) -> bool:
        return hp <= 0

    while not battle.is_over:
        print(f"\n=== Turn {battle.turn_number} ===")
        print(f"Ash's {pikachu.name}: {pikachu.current_hp}/{pikachu.max_hp} HP")
        print(f"Gary's {charizard.name}: {charizard.current_hp}/{charizard.max_hp} HP")

        events: list[TurnEvent] = []
        order = (
            [battle.trainer_a, battle.trainer_b]
            if pikachu.speed >= charizard.speed
            else [battle.trainer_b, battle.trainer_a]
        )

        for trainer in order:
            attacker = trainer.active_vibemon
            defender = (
                battle.trainer_b.active_vibemon if trainer == battle.trainer_a else battle.trainer_a.active_vibemon
            )

            if attacker.status == StatusConditionT.SLEEP:
                attacker.sleep_turns_remaining -= 1
                if attacker.sleep_turns_remaining <= 0:
                    attacker.status = StatusConditionT.NONE
                    events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} woke up!"))
                else:
                    events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} is asleep!"))
                continue

            if attacker.status == StatusConditionT.FREEZE:
                import random

                if random.random() < 0.2:
                    attacker.status = StatusConditionT.NONE
                    events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} thawed out!"))
                else:
                    events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} is frozen!"))
                continue

            if attacker.status == StatusConditionT.PARALYSIS:
                import random

                if random.random() < 0.25:
                    events.append(
                        TurnEvent(actor=attacker.name, description=f"{attacker.name} is paralyzed and can't move!")
                    )
                    continue

            if attacker.is_flinched:
                attacker.is_flinched = False
                events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} flinched!"))
                continue

            if attacker.is_confused:
                import random

                attacker.confusion_turns -= 1
                if attacker.confusion_turns <= 0:
                    attacker.is_confused = False
                    events.append(TurnEvent(actor=attacker.name, description=f"{attacker.name} is no longer confused!"))
                else:
                    if random.random() < 0.5:
                        dmg = attacker.max_hp // 4
                        attacker.current_hp = max(0, attacker.current_hp - dmg)
                        events.append(
                            TurnEvent(
                                actor=attacker.name,
                                description=f"{attacker.name} hurt itself in confusion!",
                                hp_delta=-dmg,
                            )
                        )
                        if will_faint(attacker.current_hp):
                            attacker.status = StatusConditionT.FAINTED
                            events.append(TurnEvent(actor=attacker.name, fainted=True))
                            break
                        continue

            move = attacker.moves[0]
            move.pp_current -= 1

            import random

            if move.accuracy and random.random() > move.accuracy:
                events.append(
                    TurnEvent(
                        actor=attacker.name,
                        missed=True,
                        move_used=move.name,
                        description=f"{attacker.name}'s {move.name} missed!",
                    )
                )
                continue

            damage = calc_damage(attacker, defender, move)
            defender.current_hp = max(0, defender.current_hp - damage)

            type_eff = type_modifier(attacker, defender, move)
            eff_text = " super effective!" if type_eff > 1 else " not very effective..." if type_eff < 1 else ""

            events.append(
                TurnEvent(
                    actor=attacker.name,
                    move_used=move.name,
                    hp_delta=-damage,
                    description=f"{attacker.name} used {move.name}! {damage} damage{eff_text}",
                )
            )

            if move.effect and move.effect.chance > 0:
                if random.random() < move.effect.chance:
                    if move.effect.status_inflict and defender.status == StatusConditionT.NONE:
                        defender.status = move.effect.status_inflict
                        events.append(
                            TurnEvent(
                                actor=attacker.name,
                                status_change=defender.status,
                                description=f"{defender.name} got {defender.status.value}!",
                            )
                        )

                    for stat, change in move.effect.stat_changes.items():
                        if hasattr(defender.stat_stages, stat):
                            setattr(
                                defender.stat_stages,
                                stat,
                                max(-6, min(6, getattr(defender.stat_stages, stat) + change)),
                            )
                            if change < 0:
                                events.append(
                                    TurnEvent(
                                        actor=attacker.name,
                                        stat_stage_changes={stat: change},
                                        description=f"{defender.name}'s {stat} fell!",
                                    )
                                )

            if defender.is_fainted:
                defender.status = StatusConditionT.FAINTED
                events.append(TurnEvent(actor=defender.name, fainted=True, description=f"{defender.name} fainted!"))
                break

        dmg_a = apply_status_damage(pikachu)
        if dmg_a > 0:
            events.append(
                TurnEvent(
                    actor=pikachu.name, hp_delta=-dmg_a, description=f"{pikachu.name} takes poison damage: {dmg_a}"
                )
            )
            if pikachu.is_fainted:
                events.append(TurnEvent(actor=pikachu.name, fainted=True))

        dmg_b = apply_status_damage(charizard)
        if dmg_b > 0:
            events.append(
                TurnEvent(
                    actor=charizard.name, hp_delta=-dmg_b, description=f"{charizard.name} takes poison damage: {dmg_b}"
                )
            )
            if charizard.is_fainted:
                events.append(TurnEvent(actor=charizard.name, fainted=True))

        for e in events:
            print(e.description)

        battle.turn_history.append(TurnRecord(turn_number=battle.turn_number, events=events))

        if charizard.is_fainted:
            battle.winner = battle.trainer_a.id
            print(f"\n*** {battle.trainer_a.name} wins! ***")
            break
        if pikachu.is_fainted:
            battle.winner = battle.trainer_b.id
            print(f"\n*** {battle.trainer_b.name} wins! ***")
            break

        battle.turn_number += 1

    print(
        f"\nFinal state: {pikachu.name} {pikachu.current_hp}/{pikachu.max_hp} | {charizard.name} {charizard.current_hp}/{charizard.max_hp}"
    )
