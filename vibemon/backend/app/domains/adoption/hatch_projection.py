"""Hatch review read-model assembly from public Vibemon payloads."""

from typing import Literal
import uuid

from app.core.schema import Schema
from app.domains.adoption import schema as adoption_schema
from app.domains.move.entity import Move
from app.domains.vibemon import types as vibemon_types
from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.identity import BaseStats
from app.domains.vibemon.schema import PublicVibemon
from app.domains.vibemon.strength_formulas import power_pips
from app.domains.vibemon.types import VibemonLifecycleT


class BaseStatsRead(Schema):
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    total: int


type LineRarityT = Literal["normal", "deep"]

_SIZE_FACTOR_BASE = 0.36
_SIZE_FACTOR_EVO_SPAN = 0.34
_SIZE_FACTOR_BST_FLOOR = 260
_SIZE_FACTOR_BST_CEILING = 620
_SIZE_FACTOR_BST_SPAN = 0.30
_SIZE_FACTOR_STR_SPAN = 0.14
_SIZE_FACTOR_MIN = 0.36
_SIZE_FACTOR_MAX = 1.32


class CandidateDisplayRead(Schema):
    """Placement hints for rendering the candidate sprite on the platform."""

    anchor_x: float | None = None
    baseline_y: float | None = None
    size_factor: float = 0.7


class MoveRead(Schema):
    """Move summary for the hatch review Moves tab."""

    name: str
    element: str
    category: str
    power: int | None = None
    pp: int = 10
    flavor_text: str = ""
    accuracy: float | None = None
    priority: int = 0
    combat_hints: tuple[str, ...] = ()


class EvolutionLineRead(Schema):
    """Structured evolution-line facts; the UI owns the player copy."""

    form_index: int
    form_count: int
    line_rarity: LineRarityT


class HatchCandidateRead(Schema):
    """Candidate payload tailored for the hatch review UI."""

    id: uuid.UUID
    name: str
    nickname: str | None = None
    elements: tuple[str, ...]
    base_stats: BaseStatsRead
    bst: int
    power_pips: int
    is_radiant: bool
    evo_seed: int
    evolution_line: EvolutionLineRead
    moves: tuple[MoveRead, ...] = ()
    display: CandidateDisplayRead
    lifecycle: VibemonLifecycleT
    reference_url: str | None = None
    reference_facing: str = "left"
    providers: tuple[str, ...] = ()
    candidate_review: adoption_schema.CandidateReviewRead | None = None


class CandidateActionRead(Schema):
    candidate: HatchCandidateRead
    crew_count: int


_FORM_COUNTS: dict[vibemon_types.EvolutionStageT, int] = {
    vibemon_types.EvolutionStageT.BASE: 1,
    vibemon_types.EvolutionStageT.STAGE_2: 2,
    vibemon_types.EvolutionStageT.STAGE_3: 3,
    vibemon_types.EvolutionStageT.PSEUDO_LEGENDARY: 3,
    vibemon_types.EvolutionStageT.LEGENDARY: 1,
    vibemon_types.EvolutionStageT.ULTRA_LEGENDARY: 1,
}

_STAGE_FORM_INDEX: dict[vibemon_types.EvolutionStageT, int] = {
    vibemon_types.EvolutionStageT.BASE: 1,
    vibemon_types.EvolutionStageT.STAGE_2: 2,
    vibemon_types.EvolutionStageT.STAGE_3: 3,
}


def evolution_form_index(
    *,
    evo_seed: vibemon_types.EvolutionStageT,
    evo_stage: vibemon_types.EvolutionStageT,
) -> int:
    """Map the mon's current stage to its 1-based slot within the evolution line."""
    if evo_seed in (
        vibemon_types.EvolutionStageT.BASE,
        vibemon_types.EvolutionStageT.LEGENDARY,
        vibemon_types.EvolutionStageT.ULTRA_LEGENDARY,
    ):
        return 1
    return _STAGE_FORM_INDEX.get(evo_stage, 1)


def hatch_display_size_factor(
    *,
    form_index: int,
    form_count: int,
    bst: int,
    power_pips: int,
) -> float:
    """Trainer-relative sprite height from evolution progress, raw BST, and STR pips."""
    count = max(form_count, 1)
    index = min(max(form_index, 1), count)
    evo_progress = index / count

    bst_span = _SIZE_FACTOR_BST_CEILING - _SIZE_FACTOR_BST_FLOOR
    bst_norm = (bst - _SIZE_FACTOR_BST_FLOOR) / bst_span if bst_span > 0 else 0.0
    bst_norm = min(max(bst_norm, 0.0), 1.0)

    pips = min(max(power_pips, 1), 3)
    str_progress = (pips - 1) / 2

    factor = (
        _SIZE_FACTOR_BASE
        + evo_progress * _SIZE_FACTOR_EVO_SPAN
        + bst_norm * _SIZE_FACTOR_BST_SPAN
        + str_progress * _SIZE_FACTOR_STR_SPAN
    )
    return round(min(max(factor, _SIZE_FACTOR_MIN), _SIZE_FACTOR_MAX), 4)


def base_stats_read(base: BaseStats) -> BaseStatsRead:
    return BaseStatsRead(
        hp=base.hp,
        attack=base.attack,
        defense=base.defense,
        sp_attack=base.sp_attack,
        sp_defense=base.sp_defense,
        speed=base.speed,
        total=base.total,
    )


def evolution_line_read(
    evo_seed: vibemon_types.EvolutionStageT,
    *,
    evo_stage: vibemon_types.EvolutionStageT,
) -> EvolutionLineRead:
    deep = evo_seed is vibemon_types.EvolutionStageT.PSEUDO_LEGENDARY
    return EvolutionLineRead(
        form_index=evolution_form_index(evo_seed=evo_seed, evo_stage=evo_stage),
        form_count=_FORM_COUNTS.get(evo_seed, 1),
        line_rarity="deep" if deep else "normal",
    )


def _effect_hint(effect: object, *, chance: float) -> str | None:
    from app.domains.move import entity as move_entity

    lead = f"{int(chance * 100)}% chance to " if chance < 1.0 else ""
    match effect:
        case move_entity.StatusInflict(status=status):
            label = status.value.replace("_", " ")
            return f"{lead}inflict {label}."
        case move_entity.StatChange(changes=changes):
            parts = [f"{'+' if delta > 0 else ''}{delta} {stat.replace('_', ' ')}" for stat, delta in changes.items()]
            return f"{lead}{', '.join(parts)}."
        case move_entity.Drain(ratio=ratio):
            return f"{lead}drain {int(ratio * 100)}% of damage as HP."
        case move_entity.Recoil(ratio=ratio):
            return f"{lead}recoil {int(ratio * 100)}% of damage."
        case move_entity.WeatherSet(weather=weather):
            return f"{lead}set {weather.value.replace('_', ' ')} weather."
        case move_entity.Heal(ratio=ratio):
            return f"{lead}heal {int(ratio * 100)}% max HP."
        case _:
            return None


def _move_combat_hints(move: Move) -> tuple[str, ...]:
    hints: list[str] = []
    if move.accuracy is None:
        hints.append("Never misses.")
    elif move.accuracy < 1.0:
        hints.append(f"Accuracy {round(move.accuracy * 100)}%.")
    if move.priority != 0:
        sign = "+" if move.priority > 0 else ""
        hints.append(f"Priority {sign}{move.priority}.")
    for group in move.effects:
        for effect in group.effects:
            text = _effect_hint(effect, chance=group.chance)
            if text:
                hints.append(text)
    return tuple(hints)


def move_read(move: Move) -> MoveRead:
    return MoveRead(
        name=move.name,
        element=move.type.value,
        category=move.category.value,
        power=move.power,
        pp=move.pp,
        flavor_text=move.flavor_text,
        accuracy=move.accuracy,
        priority=move.priority,
        combat_hints=_move_combat_hints(move),
    )


def assemble_hatch_candidate(
    vibemon: PublicVibemon,
    *,
    reference_facing: str = "left",
) -> HatchCandidateRead:
    reference = next(
        (asset for asset in vibemon.assets if asset.kind == AssetKind.REFERENCE),
        None,
    )
    evo_seed = vibemon.identity.evo_seed
    strength_pips = power_pips(evo_seed, vibemon.identity.bst)
    evolution_line = evolution_line_read(evo_seed, evo_stage=vibemon.evo_stage)
    return HatchCandidateRead(
        id=vibemon.id,
        name=vibemon.name,
        nickname=vibemon.nickname,
        elements=tuple(element.value for element in vibemon.identity.elements),
        base_stats=base_stats_read(vibemon.identity.base),
        bst=vibemon.identity.bst,
        power_pips=strength_pips,
        is_radiant=vibemon.identity.is_radiant,
        evo_seed=int(evo_seed),
        evolution_line=evolution_line,
        moves=tuple(move_read(move) for move in vibemon.moves),
        display=CandidateDisplayRead(
            anchor_x=reference.anchor.anchor_x if reference and reference.anchor else None,
            baseline_y=reference.anchor.baseline_y if reference and reference.anchor else None,
            size_factor=hatch_display_size_factor(
                form_index=evolution_line.form_index,
                form_count=evolution_line.form_count,
                bst=vibemon.identity.bst,
                power_pips=strength_pips,
            ),
        ),
        lifecycle=vibemon.lifecycle,
        reference_url=reference.url if reference else None,
        reference_facing=reference_facing,
        providers=vibemon.birth_providers,
        candidate_review=vibemon.candidate_review,
    )
