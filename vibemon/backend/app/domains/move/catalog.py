from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.types import BaseStatNameT

type StatGradeT = Literal["S", "A", "B", "C", "D"]

# S/A/B/C/D mapped to integer weights. Each grade owns a 0.3-wide band centered
# on midpoint = (weight * 2 - 1) / 10 → D=0.1, C=0.3, B=0.5, A=0.7, S=0.9.
GRADE_WEIGHT: dict[StatGradeT, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

# Per-element stat affinity. An element's S/A stats trend high; D stats trend low.
# Used to bias base-stat distribution during Identity generation. Dual-type Vibemon
# average the two elements' grade weights per stat.
ELEMENT_STAT_GRADE: dict[VibemonTypeT, dict[BaseStatNameT, StatGradeT]] = {
    VibemonTypeT.DRAGON: {
        "hp": "S",
        "attack": "S",
        "defense": "A",
        "sp_attack": "S",
        "sp_defense": "S",
        "speed": "A",
    },
    VibemonTypeT.STEEL: {
        "hp": "B",
        "attack": "A",
        "defense": "S",
        "sp_attack": "B",
        "sp_defense": "A",
        "speed": "D",
    },
    VibemonTypeT.FIGHTING: {
        "hp": "A",
        "attack": "S",
        "defense": "B",
        "sp_attack": "D",
        "sp_defense": "C",
        "speed": "B",
    },
    VibemonTypeT.PSYCHIC: {
        "hp": "C",
        "attack": "D",
        "defense": "C",
        "sp_attack": "S",
        "sp_defense": "S",
        "speed": "B",
    },
    VibemonTypeT.ELECTRIC: {
        "hp": "D",
        "attack": "C",
        "defense": "D",
        "sp_attack": "A",
        "sp_defense": "B",
        "speed": "S",
    },
    VibemonTypeT.FLYING: {
        "hp": "B",
        "attack": "B",
        "defense": "D",
        "sp_attack": "B",
        "sp_defense": "C",
        "speed": "S",
    },
    VibemonTypeT.ROCK: {
        "hp": "B",
        "attack": "A",
        "defense": "S",
        "sp_attack": "D",
        "sp_defense": "B",
        "speed": "D",
    },
    VibemonTypeT.ICE: {
        "hp": "A",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "C",
    },
    VibemonTypeT.NORMAL: {
        "hp": "S",
        "attack": "C",
        "defense": "D",
        "sp_attack": "D",
        "sp_defense": "D",
        "speed": "B",
    },
    VibemonTypeT.GHOST: {
        "hp": "D",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "C",
    },
    VibemonTypeT.GROUND: {
        "hp": "A",
        "attack": "A",
        "defense": "A",
        "sp_attack": "D",
        "sp_defense": "D",
        "speed": "D",
    },
    VibemonTypeT.FIRE: {
        "hp": "C",
        "attack": "B",
        "defense": "C",
        "sp_attack": "A",
        "sp_defense": "B",
        "speed": "B",
    },
    VibemonTypeT.FAIRY: {
        "hp": "C",
        "attack": "D",
        "defense": "C",
        "sp_attack": "B",
        "sp_defense": "A",
        "speed": "C",
    },
    VibemonTypeT.WATER: {
        "hp": "B",
        "attack": "C",
        "defense": "B",
        "sp_attack": "C",
        "sp_defense": "B",
        "speed": "C",
    },
    VibemonTypeT.DARK: {
        "hp": "B",
        "attack": "A",
        "defense": "C",
        "sp_attack": "B",
        "sp_defense": "D",
        "speed": "A",
    },
    VibemonTypeT.POISON: {
        "hp": "C",
        "attack": "C",
        "defense": "C",
        "sp_attack": "C",
        "sp_defense": "C",
        "speed": "C",
    },
    VibemonTypeT.GRASS: {
        "hp": "C",
        "attack": "B",
        "defense": "B",
        "sp_attack": "B",
        "sp_defense": "B",
        "speed": "D",
    },
    VibemonTypeT.BUG: {
        "hp": "D",
        "attack": "D",
        "defense": "C",
        "sp_attack": "D",
        "sp_defense": "C",
        "speed": "C",
    },
}


ELEMENT_CHART: dict[tuple[VibemonTypeT, VibemonTypeT], float] = {
    (VibemonTypeT.NORMAL, VibemonTypeT.ROCK): 0.5,
    (VibemonTypeT.NORMAL, VibemonTypeT.GHOST): 0.0,
    (VibemonTypeT.NORMAL, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.FIRE, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.FIRE, VibemonTypeT.WATER): 0.5,
    (VibemonTypeT.FIRE, VibemonTypeT.GRASS): 2.0,
    (VibemonTypeT.FIRE, VibemonTypeT.ICE): 2.0,
    (VibemonTypeT.FIRE, VibemonTypeT.BUG): 2.0,
    (VibemonTypeT.FIRE, VibemonTypeT.ROCK): 0.5,
    (VibemonTypeT.FIRE, VibemonTypeT.DRAGON): 0.5,
    (VibemonTypeT.WATER, VibemonTypeT.FIRE): 2.0,
    (VibemonTypeT.WATER, VibemonTypeT.WATER): 0.5,
    (VibemonTypeT.WATER, VibemonTypeT.GRASS): 0.5,
    (VibemonTypeT.WATER, VibemonTypeT.GROUND): 2.0,
    (VibemonTypeT.WATER, VibemonTypeT.ROCK): 2.0,
    (VibemonTypeT.WATER, VibemonTypeT.DRAGON): 0.5,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.WATER): 2.0,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.ELECTRIC): 0.5,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.GRASS): 0.5,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.GROUND): 0.0,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.FLYING): 2.0,
    (VibemonTypeT.ELECTRIC, VibemonTypeT.DRAGON): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.WATER): 2.0,
    (VibemonTypeT.GRASS, VibemonTypeT.GRASS): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.POISON): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.GROUND): 2.0,
    (VibemonTypeT.GRASS, VibemonTypeT.FLYING): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.BUG): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.ROCK): 2.0,
    (VibemonTypeT.GRASS, VibemonTypeT.DRAGON): 0.5,
    (VibemonTypeT.GRASS, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.ICE, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.ICE, VibemonTypeT.WATER): 0.5,
    (VibemonTypeT.ICE, VibemonTypeT.GRASS): 2.0,
    (VibemonTypeT.ICE, VibemonTypeT.ICE): 0.5,
    (VibemonTypeT.ICE, VibemonTypeT.GROUND): 2.0,
    (VibemonTypeT.ICE, VibemonTypeT.FLYING): 2.0,
    (VibemonTypeT.ICE, VibemonTypeT.DRAGON): 2.0,
    (VibemonTypeT.ICE, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.FIGHTING, VibemonTypeT.NORMAL): 2.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.ICE): 2.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.POISON): 0.5,
    (VibemonTypeT.FIGHTING, VibemonTypeT.FLYING): 0.5,
    (VibemonTypeT.FIGHTING, VibemonTypeT.PSYCHIC): 0.5,
    (VibemonTypeT.FIGHTING, VibemonTypeT.BUG): 0.5,
    (VibemonTypeT.FIGHTING, VibemonTypeT.ROCK): 2.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.GHOST): 0.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.DARK): 2.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.STEEL): 2.0,
    (VibemonTypeT.FIGHTING, VibemonTypeT.FAIRY): 0.5,
    (VibemonTypeT.POISON, VibemonTypeT.GRASS): 2.0,
    (VibemonTypeT.POISON, VibemonTypeT.POISON): 0.5,
    (VibemonTypeT.POISON, VibemonTypeT.GROUND): 0.5,
    (VibemonTypeT.POISON, VibemonTypeT.ROCK): 0.5,
    (VibemonTypeT.POISON, VibemonTypeT.GHOST): 0.5,
    (VibemonTypeT.POISON, VibemonTypeT.STEEL): 0.0,
    (VibemonTypeT.POISON, VibemonTypeT.FAIRY): 2.0,
    (VibemonTypeT.GROUND, VibemonTypeT.FIRE): 2.0,
    (VibemonTypeT.GROUND, VibemonTypeT.ELECTRIC): 2.0,
    (VibemonTypeT.GROUND, VibemonTypeT.GRASS): 0.5,
    (VibemonTypeT.GROUND, VibemonTypeT.POISON): 2.0,
    (VibemonTypeT.GROUND, VibemonTypeT.FLYING): 0.0,
    (VibemonTypeT.GROUND, VibemonTypeT.BUG): 0.5,
    (VibemonTypeT.GROUND, VibemonTypeT.ROCK): 2.0,
    (VibemonTypeT.GROUND, VibemonTypeT.STEEL): 2.0,
    (VibemonTypeT.FLYING, VibemonTypeT.ELECTRIC): 0.5,
    (VibemonTypeT.FLYING, VibemonTypeT.GRASS): 2.0,
    (VibemonTypeT.FLYING, VibemonTypeT.FIGHTING): 2.0,
    (VibemonTypeT.FLYING, VibemonTypeT.BUG): 2.0,
    (VibemonTypeT.FLYING, VibemonTypeT.ROCK): 0.5,
    (VibemonTypeT.FLYING, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.PSYCHIC, VibemonTypeT.FIGHTING): 2.0,
    (VibemonTypeT.PSYCHIC, VibemonTypeT.POISON): 2.0,
    (VibemonTypeT.PSYCHIC, VibemonTypeT.PSYCHIC): 0.5,
    (VibemonTypeT.PSYCHIC, VibemonTypeT.DARK): 0.0,
    (VibemonTypeT.PSYCHIC, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.GRASS): 2.0,
    (VibemonTypeT.BUG, VibemonTypeT.FIGHTING): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.POISON): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.FLYING): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.PSYCHIC): 2.0,
    (VibemonTypeT.BUG, VibemonTypeT.GHOST): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.DARK): 2.0,
    (VibemonTypeT.BUG, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.BUG, VibemonTypeT.FAIRY): 0.5,
    (VibemonTypeT.ROCK, VibemonTypeT.FIRE): 2.0,
    (VibemonTypeT.ROCK, VibemonTypeT.ICE): 2.0,
    (VibemonTypeT.ROCK, VibemonTypeT.FIGHTING): 0.5,
    (VibemonTypeT.ROCK, VibemonTypeT.GROUND): 0.5,
    (VibemonTypeT.ROCK, VibemonTypeT.FLYING): 2.0,
    (VibemonTypeT.ROCK, VibemonTypeT.BUG): 2.0,
    (VibemonTypeT.ROCK, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.GHOST, VibemonTypeT.NORMAL): 0.0,
    (VibemonTypeT.GHOST, VibemonTypeT.PSYCHIC): 2.0,
    (VibemonTypeT.GHOST, VibemonTypeT.GHOST): 2.0,
    (VibemonTypeT.GHOST, VibemonTypeT.DARK): 0.5,
    (VibemonTypeT.DRAGON, VibemonTypeT.DRAGON): 2.0,
    (VibemonTypeT.DRAGON, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.DRAGON, VibemonTypeT.FAIRY): 0.0,
    (VibemonTypeT.DARK, VibemonTypeT.PSYCHIC): 2.0,
    (VibemonTypeT.DARK, VibemonTypeT.GHOST): 2.0,
    (VibemonTypeT.DARK, VibemonTypeT.DARK): 0.5,
    (VibemonTypeT.DARK, VibemonTypeT.FAIRY): 0.5,
    (VibemonTypeT.STEEL, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.STEEL, VibemonTypeT.WATER): 0.5,
    (VibemonTypeT.STEEL, VibemonTypeT.ELECTRIC): 0.5,
    (VibemonTypeT.STEEL, VibemonTypeT.ICE): 2.0,
    (VibemonTypeT.STEEL, VibemonTypeT.ROCK): 2.0,
    (VibemonTypeT.STEEL, VibemonTypeT.STEEL): 0.5,
    (VibemonTypeT.STEEL, VibemonTypeT.FAIRY): 2.0,
    (VibemonTypeT.FAIRY, VibemonTypeT.FIRE): 0.5,
    (VibemonTypeT.FAIRY, VibemonTypeT.FIGHTING): 2.0,
    (VibemonTypeT.FAIRY, VibemonTypeT.POISON): 0.5,
    (VibemonTypeT.FAIRY, VibemonTypeT.DRAGON): 2.0,
    (VibemonTypeT.FAIRY, VibemonTypeT.DARK): 2.0,
    (VibemonTypeT.FAIRY, VibemonTypeT.STEEL): 0.5,
}


@dataclass(frozen=True, slots=True)
class TypeAffinity:
    covers: frozenset[VibemonTypeT]
    weak_to: frozenset[VibemonTypeT]
    resists: frozenset[VibemonTypeT]


def _derive_type_affinities(
    element_chart: dict[tuple[VibemonTypeT, VibemonTypeT], float],
) -> dict[VibemonTypeT, TypeAffinity]:
    all_types = tuple(VibemonTypeT)
    covers_by_attack_type: dict[VibemonTypeT, set[VibemonTypeT]] = {attack_type: set() for attack_type in all_types}
    weak_to_by_defender_type: dict[VibemonTypeT, set[VibemonTypeT]] = {
        defender_type: set() for defender_type in all_types
    }
    resists_by_defender_type: dict[VibemonTypeT, set[VibemonTypeT]] = {
        defender_type: set() for defender_type in all_types
    }

    for attack_type in all_types:
        for defender_type in all_types:
            modifier = element_chart.get((attack_type, defender_type), 1.0)
            if modifier > 1.0:
                covers_by_attack_type[attack_type].add(defender_type)
                weak_to_by_defender_type[defender_type].add(attack_type)
            elif 0.0 < modifier < 1.0:
                resists_by_defender_type[defender_type].add(attack_type)

    return {
        element_type: TypeAffinity(
            covers=frozenset(covers_by_attack_type[element_type]),
            weak_to=frozenset(weak_to_by_defender_type[element_type]),
            resists=frozenset(resists_by_defender_type[element_type]),
        )
        for element_type in all_types
    }


TYPE_AFFINITIES: dict[VibemonTypeT, TypeAffinity] = _derive_type_affinities(ELEMENT_CHART)

# Centralized move-assignment tuning constants.
MOVE_ASSIGNMENT_SAME_TYPE_BONUS = 2.0
MOVE_ASSIGNMENT_NORMAL_BONUS = 1.0
MOVE_ASSIGNMENT_ANTAGONISTIC_BONUS = 0.5
MOVE_ASSIGNMENT_COVERAGE_BONUS = 1.5


def get_element_effectiveness(attack_type: VibemonTypeT, defender_elements: Sequence[VibemonTypeT]) -> float:
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
    move_type: VibemonTypeT,
    vibemon_elements: Sequence[VibemonTypeT],
) -> float:
    """
    Bonus multiplier for assigning a move to a vibemon.

    Same type:  2.0x (thematic fit)
    Coverage:   1.5x (fills defensive gaps)
    Normal:     1.0x (utility, no bonus/penalty)
    Other:      0.5x (antagonistic)
    """
    if move_type in vibemon_elements:
        return MOVE_ASSIGNMENT_SAME_TYPE_BONUS

    defensive_gaps = {
        attacker for vibemon_element in vibemon_elements for attacker in TYPE_AFFINITIES[vibemon_element].weak_to
    }
    move_coverage = TYPE_AFFINITIES[move_type].covers
    if defensive_gaps & move_coverage:
        return MOVE_ASSIGNMENT_COVERAGE_BONUS

    if move_type == VibemonTypeT.NORMAL:
        return MOVE_ASSIGNMENT_NORMAL_BONUS
    return MOVE_ASSIGNMENT_ANTAGONISTIC_BONUS
