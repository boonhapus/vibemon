import random

from app.domains.battle import entity as battle_entity
from app.domains.move import entity as move_entity
from app.domains.move import types as move_types
from app.domains.vibemon.identity import BaseStats, Identity
from scripts import _common


def _move(
    name: str,
    *,
    move_type: move_types.VibemonTypeT,
    category: move_types.MoveCategoryT = move_types.MoveCategoryT.PHYSICAL,
    power: int | None = 40,
    effects: tuple[move_entity.EffectGroup, ...] = (),
) -> move_entity.Move:
    return move_entity.Move(
        id=f"test.{name.casefold().replace(' ', '_')}",
        name=name,
        flavor_text="A test move.",
        type=move_type,
        category=category,
        power=power,
        accuracy=1.0,
        effects=effects,
    )


def _vibemon(
    *,
    elements: tuple[move_types.VibemonTypeT, ...],
    moves: tuple[move_entity.Move, ...],
) -> battle_entity.BattleVibemon:
    return battle_entity.BattleVibemon(
        identity=Identity(
            name="Policy Test",
            elements=elements,
            base=BaseStats(attack=90, defense=60, sp_attack=90, sp_defense=60, speed=60),
        ),
        moves=moves,
        level=50,
    )


def test_best_damage_policy_uses_type_effectiveness() -> None:
    weak_first = _move("Weak First", move_type=move_types.VibemonTypeT.NORMAL, power=40)
    water_hit = _move("Water Hit", move_type=move_types.VibemonTypeT.WATER, power=50)
    user = _vibemon(elements=(move_types.VibemonTypeT.NORMAL,), moves=(weak_first, water_hit))
    target = _vibemon(elements=(move_types.VibemonTypeT.FIRE,), moves=(weak_first,))

    selected = _common._choose_move(user, target, policy="best_damage", rng=random.Random(1))

    assert selected.name == "Water Hit"


def test_stab_first_policy_prefers_stab_over_stronger_coverage() -> None:
    strong_water = _move("Strong Water", move_type=move_types.VibemonTypeT.WATER, power=120)
    stab_normal = _move("Stab Normal", move_type=move_types.VibemonTypeT.NORMAL, power=40)
    user = _vibemon(elements=(move_types.VibemonTypeT.NORMAL,), moves=(strong_water, stab_normal))
    target = _vibemon(elements=(move_types.VibemonTypeT.FIRE,), moves=(stab_normal,))

    selected = _common._choose_move(user, target, policy="stab_first", rng=random.Random(1))

    assert selected.name == "Stab Normal"


def test_status_aware_policy_can_pick_high_value_status_move() -> None:
    nudge = _move("Nudge", move_type=move_types.VibemonTypeT.NORMAL, power=20)
    sleep = _move(
        "Sleep",
        move_type=move_types.VibemonTypeT.PSYCHIC,
        category=move_types.MoveCategoryT.STATUS,
        power=None,
        effects=(
            move_entity.EffectGroup(
                effects=(
                    move_entity.StatusInflict(
                        status=move_types.StatusConditionT.FREEZE,
                    ),
                ),
            ),
        ),
    )
    user = _vibemon(elements=(move_types.VibemonTypeT.PSYCHIC,), moves=(nudge, sleep))
    target = _vibemon(elements=(move_types.VibemonTypeT.NORMAL,), moves=(nudge,))

    selected = _common._choose_move(user, target, policy="status_aware", rng=random.Random(1))

    assert selected.name == "Sleep"
