from collections.abc import Sequence
from typing import Literal

from app import types

type StatGradeT = Literal["S", "A", "B", "C", "D"]

# S/A/B/C/D mapped to integer weights. Each grade owns a 0.3-wide band centered
# on midpoint = (weight * 2 - 1) / 10 → D=0.1, C=0.3, B=0.5, A=0.7, S=0.9.
GRADE_WEIGHT: dict[StatGradeT, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

# Per-element stat affinity. An element's S/A stats trend high; D stats trend low.
# Used to bias base-stat distribution during Identity generation. Dual-type Vibemon
# average the two elements' grade weights per stat.
ELEMENT_STAT_GRADE: dict[types.VibemonTypeT, dict[types.BaseStatNameT, StatGradeT]] = {
    types.VibemonTypeT.DRAGON: {
        "hp": "S",
        "attack": "S",
        "defense": "A",
        "sp_attack": "S",
        "sp_defense": "S",
        "speed": "A",
    },
    types.VibemonTypeT.STEEL: {
        "hp": "B",
        "attack": "A",
        "defense": "S",
        "sp_attack": "B",
        "sp_defense": "A",
        "speed": "D",
    },
    types.VibemonTypeT.FIGHTING: {
        "hp": "A",
        "attack": "S",
        "defense": "B",
        "sp_attack": "D",
        "sp_defense": "C",
        "speed": "B",
    },
    types.VibemonTypeT.PSYCHIC: {
        "hp": "C",
        "attack": "D",
        "defense": "C",
        "sp_attack": "S",
        "sp_defense": "S",
        "speed": "B",
    },
    types.VibemonTypeT.ELECTRIC: {
        "hp": "D",
        "attack": "C",
        "defense": "D",
        "sp_attack": "A",
        "sp_defense": "B",
        "speed": "S",
    },
    types.VibemonTypeT.FLYING: {
        "hp": "B",
        "attack": "B",
        "defense": "D",
        "sp_attack": "B",
        "sp_defense": "C",
        "speed": "S",
    },
    types.VibemonTypeT.ROCK: {
        "hp": "B",
        "attack": "A",
        "defense": "S",
        "sp_attack": "D",
        "sp_defense": "B",
        "speed": "D",
    },
    types.VibemonTypeT.ICE: {
        "hp": "A",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "C",
    },
    types.VibemonTypeT.NORMAL: {
        "hp": "S",
        "attack": "C",
        "defense": "D",
        "sp_attack": "D",
        "sp_defense": "D",
        "speed": "B",
    },
    types.VibemonTypeT.GHOST: {
        "hp": "D",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "C",
    },
    types.VibemonTypeT.GROUND: {
        "hp": "A",
        "attack": "A",
        "defense": "A",
        "sp_attack": "D",
        "sp_defense": "D",
        "speed": "D",
    },
    types.VibemonTypeT.FIRE: {
        "hp": "C",
        "attack": "B",
        "defense": "C",
        "sp_attack": "A",
        "sp_defense": "B",
        "speed": "B",
    },
    types.VibemonTypeT.FAIRY: {
        "hp": "C",
        "attack": "D",
        "defense": "C",
        "sp_attack": "B",
        "sp_defense": "A",
        "speed": "C",
    },
    types.VibemonTypeT.WATER: {
        "hp": "B",
        "attack": "C",
        "defense": "B",
        "sp_attack": "C",
        "sp_defense": "B",
        "speed": "C",
    },
    types.VibemonTypeT.DARK: {
        "hp": "B",
        "attack": "A",
        "defense": "C",
        "sp_attack": "B",
        "sp_defense": "D",
        "speed": "A",
    },
    types.VibemonTypeT.POISON: {
        "hp": "C",
        "attack": "C",
        "defense": "C",
        "sp_attack": "C",
        "sp_defense": "C",
        "speed": "C",
    },
    types.VibemonTypeT.GRASS: {
        "hp": "C",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "D",
    },
    types.VibemonTypeT.BUG: {
        "hp": "D",
        "attack": "D",
        "defense": "C",
        "sp_attack": "D",
        "sp_defense": "C",
        "speed": "C",
    },
}


ELEMENT_CHART: dict[tuple[types.VibemonTypeT, types.VibemonTypeT], float] = {
    (types.VibemonTypeT.NORMAL, types.VibemonTypeT.ROCK): 0.5,
    (types.VibemonTypeT.NORMAL, types.VibemonTypeT.GHOST): 0.0,
    (types.VibemonTypeT.NORMAL, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.WATER): 0.5,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.GRASS): 2.0,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.ICE): 2.0,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.BUG): 2.0,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.ROCK): 0.5,
    (types.VibemonTypeT.FIRE, types.VibemonTypeT.DRAGON): 0.5,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.FIRE): 2.0,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.WATER): 0.5,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.GRASS): 0.5,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.GROUND): 2.0,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.ROCK): 2.0,
    (types.VibemonTypeT.WATER, types.VibemonTypeT.DRAGON): 0.5,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.WATER): 2.0,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.ELECTRIC): 0.5,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.GRASS): 0.5,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.GROUND): 0.0,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.FLYING): 2.0,
    (types.VibemonTypeT.ELECTRIC, types.VibemonTypeT.DRAGON): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.WATER): 2.0,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.GRASS): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.POISON): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.GROUND): 2.0,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.FLYING): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.BUG): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.ROCK): 2.0,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.DRAGON): 0.5,
    (types.VibemonTypeT.GRASS, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.WATER): 0.5,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.GRASS): 2.0,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.ICE): 0.5,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.GROUND): 2.0,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.FLYING): 2.0,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.DRAGON): 2.0,
    (types.VibemonTypeT.ICE, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.NORMAL): 2.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.ICE): 2.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.POISON): 0.5,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.FLYING): 0.5,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.PSYCHIC): 0.5,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.BUG): 0.5,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.ROCK): 2.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.GHOST): 0.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.DARK): 2.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.STEEL): 2.0,
    (types.VibemonTypeT.FIGHTING, types.VibemonTypeT.FAIRY): 0.5,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.GRASS): 2.0,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.POISON): 0.5,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.GROUND): 0.5,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.ROCK): 0.5,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.GHOST): 0.5,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.STEEL): 0.0,
    (types.VibemonTypeT.POISON, types.VibemonTypeT.FAIRY): 2.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.FIRE): 2.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.ELECTRIC): 2.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.GRASS): 0.5,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.POISON): 2.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.FLYING): 0.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.BUG): 0.5,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.ROCK): 2.0,
    (types.VibemonTypeT.GROUND, types.VibemonTypeT.STEEL): 2.0,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.ELECTRIC): 0.5,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.GRASS): 2.0,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.FIGHTING): 2.0,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.BUG): 2.0,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.ROCK): 0.5,
    (types.VibemonTypeT.FLYING, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.PSYCHIC, types.VibemonTypeT.FIGHTING): 2.0,
    (types.VibemonTypeT.PSYCHIC, types.VibemonTypeT.POISON): 2.0,
    (types.VibemonTypeT.PSYCHIC, types.VibemonTypeT.PSYCHIC): 0.5,
    (types.VibemonTypeT.PSYCHIC, types.VibemonTypeT.DARK): 0.0,
    (types.VibemonTypeT.PSYCHIC, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.GRASS): 2.0,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.FIGHTING): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.POISON): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.FLYING): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.PSYCHIC): 2.0,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.GHOST): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.DARK): 2.0,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.BUG, types.VibemonTypeT.FAIRY): 0.5,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.FIRE): 2.0,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.ICE): 2.0,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.FIGHTING): 0.5,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.GROUND): 0.5,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.FLYING): 2.0,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.BUG): 2.0,
    (types.VibemonTypeT.ROCK, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.GHOST, types.VibemonTypeT.NORMAL): 0.0,
    (types.VibemonTypeT.GHOST, types.VibemonTypeT.PSYCHIC): 2.0,
    (types.VibemonTypeT.GHOST, types.VibemonTypeT.GHOST): 2.0,
    (types.VibemonTypeT.GHOST, types.VibemonTypeT.DARK): 0.5,
    (types.VibemonTypeT.DRAGON, types.VibemonTypeT.DRAGON): 2.0,
    (types.VibemonTypeT.DRAGON, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.DRAGON, types.VibemonTypeT.FAIRY): 0.0,
    (types.VibemonTypeT.DARK, types.VibemonTypeT.PSYCHIC): 2.0,
    (types.VibemonTypeT.DARK, types.VibemonTypeT.GHOST): 2.0,
    (types.VibemonTypeT.DARK, types.VibemonTypeT.DARK): 0.5,
    (types.VibemonTypeT.DARK, types.VibemonTypeT.FAIRY): 0.5,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.WATER): 0.5,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.ELECTRIC): 0.5,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.ICE): 2.0,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.ROCK): 2.0,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.STEEL): 0.5,
    (types.VibemonTypeT.STEEL, types.VibemonTypeT.FAIRY): 2.0,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.FIRE): 0.5,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.FIGHTING): 2.0,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.POISON): 0.5,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.DRAGON): 2.0,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.DARK): 2.0,
    (types.VibemonTypeT.FAIRY, types.VibemonTypeT.STEEL): 0.5,
}


def get_element_effectiveness(
    attack_type: types.VibemonTypeT, defender_elements: Sequence[types.VibemonTypeT]
) -> float:
    """
    Multiply the attacker's type modifier against each of the defender's elements.

    Dual-element defenders produce combined multipliers
      4.00x = double weakness
      0.25x = double resistance
      1.00x = neutralization, when one element is weak and the other resists
      0.00x = absolute immunity, immunity on either element trumps any weakness on the other
    """
    modifier = 1.0

    for defender_element in defender_elements:
        modifier *= ELEMENT_CHART.get((attack_type, defender_element), 1.0)

    return modifier


def get_move_assignment_bonus(
    move_type: types.VibemonTypeT,
    vibemon_elements: Sequence[types.VibemonTypeT],
) -> float:
    """
    Bonus multiplier for assigning a move to a vibemon.

    Same type:  2.0x (thematic fit)
    Normal:     1.0x (utility, no bonus/penalty)
    Other:      0.5x (antagonistic)

    TODO: When implementing TYPE_AFFINITIES, this will consider coverage
    bonuses (1.5x for moves that cover defensive gaps).
    """
    if move_type in vibemon_elements:
        return 2.0
    if move_type == types.VibemonTypeT.NORMAL:
        return 1.0
    return 0.5
