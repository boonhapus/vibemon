"""Progression resolution: XP awards, level-ups, evolution, and move offers."""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Literal
import random
import uuid

from app.core.schema import FrozenSchema
from app.domains.battle import entity
from app.domains.move.entity import Move
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon import identity as vibemon_identity
from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.progression import formulas, move_offers
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
    vibemon_name: str
    moves: tuple[Move, ...]
    requires_replace: bool
    levels_crossed: int
    phase: Literal["kit_building", "upgrade"]


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


def sample_move_learn_offer(
    vibemon: Vibemon,
    *,
    battle_id: uuid.UUID,
    provider_moves: tuple[Move, ...],
    universal_moves: tuple[Move, ...],
    learned_exclude_ids: set[str],
    element_rankings: dict[VibemonTypeT, float] | None = None,
    levels_crossed: int = 1,
    rng: random.Random | None = None,
) -> MoveLearnOffer | None:
    """Build a weighted four-choice offer from the eligible learnset pool."""
    eligible = move_offers.eligible_with_universal_fallback(
        provider_moves,
        universal_moves,
        exclude_ids=learned_exclude_ids,
        level=vibemon.level,
    )
    offer_rng = rng or move_offers.offer_rng(battle_id=battle_id, vibemon_id=vibemon.id)
    sample = move_offers.sample_move_options(
        eligible,
        elements=vibemon.identity.elements,
        element_rankings=element_rankings,
        rng=offer_rng,
    )
    if not sample:
        return None
    active_count = len(vibemon.moves)
    phase: Literal["kit_building", "upgrade"] = "kit_building" if active_count < MAX_ACTIVE_MOVES else "upgrade"
    return MoveLearnOffer(
        vibemon_id=vibemon.id,
        vibemon_name=vibemon.name,
        moves=sample,
        requires_replace=active_count >= MAX_ACTIVE_MOVES,
        levels_crossed=levels_crossed,
        phase=phase,
    )


def _apply_wild_move_learn(vibemon: Vibemon, move: Move) -> Vibemon:
    if len(vibemon.moves) < MAX_ACTIVE_MOVES:
        return vibemon.model_copy(update={"moves": (*vibemon.moves, move)})
    slot = move_offers.replacement_slot_index(vibemon.moves)
    updated_moves = list(vibemon.moves)
    updated_moves[slot] = move
    return vibemon.model_copy(update={"moves": tuple(updated_moves)})


def _combatants_by_name(battle: entity.Battle) -> dict[str, entity.Vibemon]:
    lookup: dict[str, entity.Vibemon] = {}
    for trainer in (battle.trainer_a, battle.trainer_b):
        for combatant in trainer.crew:
            lookup[combatant.name] = combatant
    return lookup


def _is_fainted(combatant: entity.BattleVibemon | Vibemon) -> bool:
    if isinstance(combatant, entity.BattleVibemon):
        return combatant.is_fainted
    return False


def _participants(battle: entity.Battle) -> tuple[entity.BattleVibemon | Vibemon, ...]:
    participants: list[entity.Vibemon] = []
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
    battle_id: uuid.UUID,
    xp_gain: int,
    provider_moves: tuple[Move, ...],
    universal_moves: tuple[Move, ...],
    learned_exclude_ids: set[str],
    auto_evolve: bool,
    element_rankings: dict[VibemonTypeT, float] | None = None,
) -> ProgressionDelta:
    """Apply XP, auto-evolve wild mons, and surface owned-mon move offers."""
    updated, xp_award = apply_xp(vibemon, xp_gain)
    evolution_applied: EvolutionApplied | None = None
    evolution_offer: EvolutionOffer | None = None
    move_learn_offer: MoveLearnOffer | None = None

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

        levels_crossed = xp_award.new_level - xp_award.previous_level
        active_count = len(updated.moves)
        offer_rng = move_offers.offer_rng(battle_id=battle_id, vibemon_id=updated.id)
        if move_offers.should_offer(
            active_move_count=active_count,
            levels_crossed=levels_crossed,
            rng=offer_rng,
        ):
            sampled_offer = sample_move_learn_offer(
                updated,
                battle_id=battle_id,
                provider_moves=provider_moves,
                universal_moves=universal_moves,
                learned_exclude_ids=learned_exclude_ids,
                element_rankings=element_rankings,
                levels_crossed=levels_crossed,
                rng=offer_rng,
            )
            if sampled_offer is not None:
                if auto_evolve:
                    pick_rng = move_offers.offer_rng(
                        battle_id=battle_id,
                        vibemon_id=updated.id,
                        salt="wild_pick",
                    )
                    picked = move_offers.auto_pick_from_sample(
                        sampled_offer.moves,
                        elements=updated.identity.elements,
                        element_rankings=element_rankings,
                        rng=pick_rng,
                    )
                    if picked is not None:
                        updated = _apply_wild_move_learn(updated, picked)
                else:
                    move_learn_offer = sampled_offer

    return ProgressionDelta(
        vibemon_id=updated.id,
        vibemon=updated,
        xp_award=xp_award,
        evolution_applied=evolution_applied,
        evolution_offer=evolution_offer,
        move_learn_offers=(move_learn_offer,) if move_learn_offer is not None else (),
    )


def resolve_battle_progression(
    battle: entity.Battle,
    *,
    battle_id: uuid.UUID,
    provider_moves_by_id: dict[uuid.UUID, tuple[Move, ...]],
    universal_moves: tuple[Move, ...],
    learned_exclude_by_id: dict[uuid.UUID, set[str]],
    auto_evolve_by_id: dict[uuid.UUID, bool],
    element_rankings_by_id: dict[uuid.UUID, dict[VibemonTypeT, float]] | None = None,
) -> BattleProgressionResult:
    """Resolve XP and progression for every battle participant."""
    xp_totals = accumulate_battle_xp(battle)
    rankings_by_id = element_rankings_by_id or {}
    deltas: list[ProgressionDelta] = []
    for combatant in _participants(battle):
        delta = resolve_progression_for_vibemon(
            combatant,
            battle_id=battle_id,
            xp_gain=xp_totals.get(combatant.id, 0),
            provider_moves=provider_moves_by_id[combatant.id],
            universal_moves=universal_moves,
            learned_exclude_ids=learned_exclude_by_id.get(combatant.id, set()),
            auto_evolve=auto_evolve_by_id.get(combatant.id, combatant.is_wild),
            element_rankings=rankings_by_id.get(combatant.id),
        )
        deltas.append(delta)
    return BattleProgressionResult(battle_id=battle_id, deltas=tuple(deltas))
