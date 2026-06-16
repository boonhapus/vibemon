"""Progression resolution: XP awards, level-ups, evolution, and move offers."""

from collections import defaultdict
from dataclasses import dataclass, field
import uuid

from app.core.schema import FrozenSchema
from app.domains.battle import entity
from app.domains.move.entity import Move
from app.domains.vibemon import identity as vibemon_identity
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.progression import formulas
from app.domains.vibemon.strength_formulas import apply_evo_seed_bst_bias
from app.domains.vibemon.types import EvolutionStageT

MAX_ACTIVE_MOVES = 4


class XpAward(FrozenSchema):
    vibemon_id: uuid.UUID
    xp_gained: int
    previous_level: int
    new_level: int
    previous_xp: int
    new_xp: int


class EvolutionOffer(FrozenSchema):
    vibemon_id: uuid.UUID
    from_stage: EvolutionStageT
    to_stage: EvolutionStageT


class EvolutionApplied(FrozenSchema):
    vibemon_id: uuid.UUID
    from_stage: EvolutionStageT
    to_stage: EvolutionStageT


class MoveLearnOffer(FrozenSchema):
    vibemon_id: uuid.UUID
    move: Move


class ProgressionDelta(FrozenSchema):
    vibemon_id: uuid.UUID
    vibemon: Vibemon
    xp_award: XpAward | None = None
    evolution_applied: EvolutionApplied | None = None
    evolution_offer: EvolutionOffer | None = None
    move_learn_offers: tuple[MoveLearnOffer, ...] = ()


class BattleProgressionResult(FrozenSchema):
    battle_id: uuid.UUID
    deltas: tuple[ProgressionDelta, ...]


@dataclass
class _XpAccumulator:
    awards: dict[uuid.UUID, int] = field(default_factory=lambda: defaultdict(int))


def learnable_moves(
    vibemon: Vibemon,
    *,
    pool: tuple[Move, ...],
    level: int,
) -> tuple[Move, ...]:
    """Moves newly eligible at ``level`` that the mon does not already know."""
    known = {move.id for move in vibemon.moves}
    return tuple(
        move for move in pool if move.level_requirement <= level and move.id not in known
    )


def apply_evolution(vibemon: Vibemon, *, to_stage: EvolutionStageT) -> Vibemon:
    """Recompute and persist base stats for a promoted ``evo_stage``."""
    stats = vibemon.identity.base.model_dump()
    scaled = apply_evo_seed_bst_bias(
        stats,
        evo_seed=vibemon.identity.evo_seed,
        evo_stage=to_stage,
    )
    return vibemon.model_copy(
        update={
            "evo_stage": to_stage,
            "identity": vibemon.identity.model_copy(update={"base": vibemon_identity.BaseStats(**scaled)}),
        }
    )


def apply_xp(vibemon: Vibemon, xp_gain: int) -> tuple[Vibemon, XpAward | None]:
    """Add XP and recompute level up to the cap."""
    if xp_gain <= 0:
        return vibemon, None
    previous_level = vibemon.level
    previous_xp = vibemon.xp
    new_xp = vibemon.xp + xp_gain
    new_level = formulas.level_from_total_xp(new_xp, growth_rate=vibemon.growth_rate)
    updated = vibemon.model_copy(update={"xp": new_xp, "level": new_level})
    return updated, XpAward(
        vibemon_id=vibemon.id,
        xp_gained=xp_gain,
        previous_level=previous_level,
        new_level=new_level,
        previous_xp=previous_xp,
        new_xp=new_xp,
    )


def _combatants_by_name(battle: entity.Battle) -> dict[str, entity.BattleVibemon]:
    lookup: dict[str, entity.BattleVibemon] = {}
    for trainer in (battle.trainer_a, battle.trainer_b):
        for combatant in trainer.crew:
            lookup[combatant.name] = combatant
    return lookup


def _is_fainted(combatant: entity.BattleVibemon | Vibemon) -> bool:
    if isinstance(combatant, entity.BattleVibemon):
        return combatant.is_fainted
    return False


def _participants(battle: entity.Battle) -> tuple[entity.BattleVibemon | Vibemon, ...]:
    participants: list[entity.BattleVibemon] = []
    for trainer in (battle.trainer_a, battle.trainer_b):
        participants.extend(trainer.crew)
    return tuple(participants)


def accumulate_battle_xp(battle: entity.Battle) -> dict[uuid.UUID, int]:
    """Disposition-agnostic XP totals from turn history faint events."""
    by_name = _combatants_by_name(battle)
    participants = _participants(battle)
    accumulator = _XpAccumulator()

    for record in battle.turn_history:
        for event in record.events:
            if event.kind != "faint" or event.source is None:
                continue
            killer = by_name.get(event.source)
            victim = by_name.get(event.target)
            if killer is None or victim is None:
                continue
            full_share = formulas.xp_award_for_faint(
                opponent_level=victim.level,
                opponent_evo_seed=victim.identity.evo_seed,
                opponent_is_trainer_owned=victim.is_owned,
            )
            if full_share <= 0:
                continue
            accumulator.awards[killer.id] += full_share
            others = [
                combatant
                for combatant in participants
                if combatant.id != killer.id and combatant.id != victim.id and not _is_fainted(combatant)
            ]
            if not others:
                continue
            share = formulas.participation_share(full_share)
            for combatant in others:
                accumulator.awards[combatant.id] += share
    return dict(accumulator.awards)


def resolve_progression_for_vibemon(
    vibemon: Vibemon,
    *,
    xp_gain: int,
    move_pool_by_level: dict[int, tuple[Move, ...]],
    auto_evolve: bool,
) -> ProgressionDelta:
    """Apply XP, auto-evolve wild mons, and surface owned-mon offers."""
    updated, xp_award = apply_xp(vibemon, xp_gain)
    evolution_applied: EvolutionApplied | None = None
    evolution_offer: EvolutionOffer | None = None
    move_offers: list[MoveLearnOffer] = []

    if xp_award is not None and xp_award.new_level > xp_award.previous_level:
        pending = formulas.pending_evolution_stage(
            level=updated.level,
            growth_rate=updated.growth_rate,
            evo_seed=updated.identity.evo_seed,
            current_stage=updated.evo_stage,
        )
        if pending is not None:
            if auto_evolve:
                updated = apply_evolution(updated, to_stage=pending)
                evolution_applied = EvolutionApplied(
                    vibemon_id=updated.id,
                    from_stage=vibemon.evo_stage,
                    to_stage=pending,
                )
            else:
                evolution_offer = EvolutionOffer(
                    vibemon_id=updated.id,
                    from_stage=updated.evo_stage,
                    to_stage=pending,
                )

        for level in range(xp_award.previous_level + 1, xp_award.new_level + 1):
            pool = move_pool_by_level.get(level, ())
            for move in learnable_moves(updated, pool=pool, level=level):
                if len(updated.moves) < MAX_ACTIVE_MOVES:
                    updated = updated.model_copy(update={"moves": (*updated.moves, move)})
                elif not auto_evolve:
                    move_offers.append(MoveLearnOffer(vibemon_id=updated.id, move=move))

    return ProgressionDelta(
        vibemon_id=updated.id,
        vibemon=updated,
        xp_award=xp_award,
        evolution_applied=evolution_applied,
        evolution_offer=evolution_offer,
        move_learn_offers=tuple(move_offers),
    )


def resolve_battle_progression(
    battle: entity.Battle,
    *,
    battle_id: uuid.UUID,
    move_pool_by_vibemon: dict[uuid.UUID, dict[int, tuple[Move, ...]]],
    auto_evolve_by_id: dict[uuid.UUID, bool],
) -> BattleProgressionResult:
    """Resolve XP and progression for every battle participant."""
    xp_totals = accumulate_battle_xp(battle)
    deltas: list[ProgressionDelta] = []
    for combatant in _participants(battle):
        delta = resolve_progression_for_vibemon(
            combatant,
            xp_gain=xp_totals.get(combatant.id, 0),
            move_pool_by_level=move_pool_by_vibemon[combatant.id],
            auto_evolve=auto_evolve_by_id.get(combatant.id, combatant.is_wild),
        )
        deltas.append(delta)
    return BattleProgressionResult(battle_id=battle_id, deltas=tuple(deltas))
