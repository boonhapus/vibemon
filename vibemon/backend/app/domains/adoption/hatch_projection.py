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


type SizeClassT = Literal["small", "mid", "large"]
type LineRarityT = Literal["normal", "deep"]


class CandidateDisplayRead(Schema):
    """Placement hints for rendering the candidate sprite on the platform."""

    anchor_x: float | None = None
    baseline_y: float | None = None
    size_class: SizeClassT = "mid"


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

_FORM_SIZE_CLASSES: dict[vibemon_types.EvolutionStageT, SizeClassT] = {
    vibemon_types.EvolutionStageT.BASE: "small",
    vibemon_types.EvolutionStageT.STAGE_2: "mid",
    vibemon_types.EvolutionStageT.STAGE_3: "large",
}

_DEEP_LINE_SEEDS: frozenset[vibemon_types.EvolutionStageT] = frozenset(
    {
        vibemon_types.EvolutionStageT.PSEUDO_LEGENDARY,
        vibemon_types.EvolutionStageT.LEGENDARY,
        vibemon_types.EvolutionStageT.ULTRA_LEGENDARY,
    }
)


def hatch_display_size_class(
    *,
    evo_seed: vibemon_types.EvolutionStageT,
    evo_stage: vibemon_types.EvolutionStageT,
) -> SizeClassT:
    """Scale hatch sprites by current form; deep lines stay visibly bigger at stage 1."""
    if evo_seed in _DEEP_LINE_SEEDS and evo_stage is vibemon_types.EvolutionStageT.BASE:
        return "large"
    return _FORM_SIZE_CLASSES.get(evo_stage, "mid")


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


def evolution_line_read(evo_seed: vibemon_types.EvolutionStageT) -> EvolutionLineRead:
    deep = evo_seed is vibemon_types.EvolutionStageT.PSEUDO_LEGENDARY
    return EvolutionLineRead(
        form_index=1,
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
    return HatchCandidateRead(
        id=vibemon.id,
        name=vibemon.name,
        nickname=vibemon.nickname,
        elements=tuple(element.value for element in vibemon.identity.elements),
        base_stats=base_stats_read(vibemon.identity.base),
        bst=vibemon.identity.bst,
        power_pips=power_pips(evo_seed, vibemon.identity.bst),
        is_radiant=vibemon.identity.is_radiant,
        evo_seed=int(evo_seed),
        evolution_line=evolution_line_read(evo_seed),
        moves=tuple(move_read(move) for move in vibemon.moves),
        display=CandidateDisplayRead(
            anchor_x=reference.anchor.anchor_x if reference and reference.anchor else None,
            baseline_y=reference.anchor.baseline_y if reference and reference.anchor else None,
            size_class=hatch_display_size_class(evo_seed=evo_seed, evo_stage=vibemon.evo_stage),
        ),
        lifecycle=vibemon.lifecycle,
        reference_url=reference.url if reference else None,
        reference_facing=reference_facing,
        providers=vibemon.birth_providers,
        candidate_review=vibemon.candidate_review,
    )
