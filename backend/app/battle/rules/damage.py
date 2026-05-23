from __future__ import annotations

from collections.abc import Iterable
from typing import Literal
import math

from app import const, types
from app.balance import element_chart
from app.battle import events, turn
from app.battle import schema as battle_schema
from app.battle.rules import stats

MOD_ONE = 4096
MOD_HALF = 2048
MOD_THREE_QUARTERS = 3072
MOD_ONE_AND_HALF = 6144


type RoundingModeT = Literal["floor", "round_half_down", "round_half_up"]


def round_half_down(value: float) -> int:
    """Nearest integer; exact .5 rounds down."""
    fraction, integer = math.modf(value)
    if fraction == 0.5:
        return int(integer)
    return round(value)


def round_half_up(value: float) -> int:
    """Nearest integer; exact .5 rounds up."""
    return math.floor(value + 0.5)


def pokemon_base_damage(level: int, power: int, attack: int, defense: int) -> int:
    """Modern mainline Pokemon base damage integer formula."""
    damage = math.floor((2 * level) / 5 + 2)
    damage = math.floor(damage * power * attack / max(1, defense))
    damage = math.floor(damage / 50)
    return damage + 2


def chain_mods(mods: Iterable[int], *, minimum: int = 1, maximum: int = 131072) -> int:
    """Chain fixed-point modifiers using Pokemon rounding."""
    chained = MOD_ONE
    for mod in mods:
        if mod != MOD_ONE:
            chained = round_half_up(chained * mod / MOD_ONE)
    return max(minimum, min(maximum, chained))


def apply_mod(value: int, mod: int) -> int:
    """Apply a fixed-point modifier using Pokemon final modifier rounding."""
    return round_half_down(value * mod / MOD_ONE)


def _is_crit(crit_stage: int, move_crit_ratio: int, ctx: turn.Turn) -> bool:
    effective_stage = min(crit_stage + move_crit_ratio, 3)
    return ctx.rng.random() < const.CRIT_THRESHOLDS[effective_stage]


def _type_modifier(effectiveness: float) -> int:
    return round(effectiveness * MOD_ONE)


def _flatten_modifiers(result: events.DamageResult) -> tuple[events.DamageModifier, ...]:
    return tuple(mod for step in result.steps for mod in step.modifiers)


def calc_damage(
    ctx: turn.Turn,
    attacker: battle_schema.BattleVibemon,
    defender: battle_schema.BattleVibemon,
    move: battle_schema.BattleMove,
    *,
    spread: bool = False,
) -> events.DamageResult:
    """Calculate damage with the modern ordered integer modifier pipeline."""
    if move.category == types.MoveCategoryT.STATUS or move.power is None:
        return events.DamageResult(
            damage=0,
            is_crit=False,
            random_roll=None,
            effectiveness=1.0,
            base_damage=0,
            steps=(),
            blocked_reason="move_failed",
        )

    if move.category == types.MoveCategoryT.PHYSICAL:
        attack = attacker.attack
        defense = defender.defense
        attack_stage_name = "attack"
        defense_stage_name = "defense"
    else:
        attack = attacker.sp_attack
        defense = defender.sp_defense
        attack_stage_name = "sp_attack"
        defense_stage_name = "sp_defense"

    is_crit = _is_crit(attacker.crit_stage, move.crit_ratio, ctx)
    attack_stage = getattr(attacker.stat_stages, attack_stage_name)
    defense_stage = getattr(defender.stat_stages, defense_stage_name)
    if is_crit:
        attack_stage = max(0, attack_stage)
        defense_stage = min(0, defense_stage)

    attack = stats.stage_modified_stat(attack, attack_stage)
    defense = stats.stage_modified_stat(defense, defense_stage)
    effectiveness = element_chart.get_element_effectiveness(move.type, defender.elements)
    if effectiveness == 0:
        return events.DamageResult(
            damage=0,
            is_crit=is_crit,
            random_roll=None,
            effectiveness=effectiveness,
            base_damage=0,
            steps=(),
            blocked_reason="type_immune",
        )

    base_damage = pokemon_base_damage(attacker.level, move.power, attack, defense)
    damage = base_damage
    steps: list[events.DamageStep] = []

    ordered: list[tuple[str, tuple[events.DamageModifier, ...], RoundingModeT]] = []
    if spread:
        ordered.append(
            (
                "spread",
                (events.DamageModifier(key="spread", numerator=MOD_THREE_QUARTERS, display=0.75),),
                "round_half_down",
            )
        )
    if is_crit:
        ordered.append(
            (
                "critical",
                (events.DamageModifier(key="critical", numerator=MOD_ONE_AND_HALF, display=1.5),),
                "round_half_down",
            )
        )

    random_roll = ctx.rng.randint(85, 100)
    ordered.append(
        (
            "random",
            (events.DamageModifier(key="random", numerator=random_roll, display=random_roll / 100),),
            "floor",
        )
    )

    if move.type in attacker.elements:
        ordered.append(
            (
                "stab",
                (events.DamageModifier(key="stab", numerator=MOD_ONE_AND_HALF, display=1.5),),
                "round_half_down",
            )
        )

    ordered.append(
        (
            "type",
            (events.DamageModifier(key="type", numerator=_type_modifier(effectiveness), display=effectiveness),),
            "round_half_down",
        )
    )

    if attacker.status == types.StatusConditionT.BURN and move.category == types.MoveCategoryT.PHYSICAL:
        ordered.append(
            (
                "burn",
                (events.DamageModifier(key="burn", numerator=MOD_HALF, display=0.5),),
                "round_half_down",
            )
        )

    for key, modifiers, rounding in ordered:
        if key == "random":
            damage = math.floor(damage * random_roll / 100)
        else:
            damage = apply_mod(damage, chain_mods(mod.numerator for mod in modifiers))
        steps.append(events.DamageStep(key=key, modifiers=modifiers, rounding=rounding, damage_after=damage))

    return events.DamageResult(
        damage=max(1, damage),
        is_crit=is_crit,
        random_roll=random_roll,
        effectiveness=effectiveness,
        base_damage=base_damage,
        steps=tuple(steps),
        blocked_reason=None,
    )


flatten_modifiers = _flatten_modifiers
