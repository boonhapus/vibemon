"""Actual Encounter workflow: pick → battle → Battle Outcome → Wild Pool adjustment."""

from dataclasses import dataclass
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BattleUnavailable
from app.core.ids import TrainerIdT
from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.encounter.wild_encounter import EncounterSelection
from app.domains.vibemon.progression import engine as progression_engine
from app.http import battle_read
from app.workflows import battle_play, wild_encounter


@dataclass(frozen=True, slots=True)
class ActualEncounterStart:
    selection: EncounterSelection
    session: battle_play.ActiveBattle


@dataclass(frozen=True, slots=True)
class ActualEncounterConclusion:
    outcome: WildEncounterOutcomeT
    progression: progression_engine.BattleProgressionResult | None


async def pick_encounter(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    latitude: float | None,
    longitude: float | None,
    crew_strength: float,
    desired_supply: int = 12,
) -> EncounterSelection | None:
    return await wild_encounter.pick_wild_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=latitude,
        longitude=longitude,
        crew_strength=crew_strength,
        desired_supply=desired_supply,
    )


async def start_encounter_battle(
    sess: AsyncSession,
    *,
    registry: battle_play.BattleSessionRegistry,
    trainer_id: TrainerIdT,
    trainer_name: str,
    hero_vibemon_id: uuid.UUID,
    wild_vibemon_id: uuid.UUID,
) -> battle_play.ActiveBattle:
    return await battle_play.start_wild_battle(
        sess,
        registry=registry,
        trainer_id=trainer_id,
        trainer_name=trainer_name,
        hero_vibemon_id=hero_vibemon_id,
        wild_vibemon_id=wild_vibemon_id,
    )


async def start_actual_encounter(
    sess: AsyncSession,
    *,
    registry: battle_play.BattleSessionRegistry,
    trainer_id: TrainerIdT,
    trainer_name: str,
    hero_vibemon_id: uuid.UUID,
    latitude: float | None,
    longitude: float | None,
    crew_strength: float,
    desired_supply: int = 12,
) -> ActualEncounterStart | None:
    """Pick a Wild Vibemon and open an interactive battle session."""
    selection = await pick_encounter(
        sess,
        trainer_id=trainer_id,
        latitude=latitude,
        longitude=longitude,
        crew_strength=crew_strength,
        desired_supply=desired_supply,
    )
    if selection is None:
        return None
    session = await start_encounter_battle(
        sess,
        registry=registry,
        trainer_id=trainer_id,
        trainer_name=trainer_name,
        hero_vibemon_id=hero_vibemon_id,
        wild_vibemon_id=selection.vibemon_id,
    )
    return ActualEncounterStart(selection=selection, session=session)


def submit_encounter_turn(
    session: battle_play.ActiveBattle,
    *,
    move_name: str,
) -> battle_read.BattleTurnRead:
    events = battle_play.submit_player_turn(session, move_name=move_name)
    return battle_read.battle_turn_read(
        session,
        events=events,
        player_trainer_id=session.player_trainer_id,
        wild_vibemon_id=session.wild_vibemon_id,
    )


def encounter_outcome_from_battle(session: battle_play.ActiveBattle) -> WildEncounterOutcomeT:
    battle = session.engine.battle
    if not battle.concluded:
        raise BattleUnavailable("Battle is not concluded.")
    if battle.winner is None:
        return WildEncounterOutcomeT.DEFEAT
    if battle.winner.id == session.player_trainer_id:
        return WildEncounterOutcomeT.WIN_NO_ADOPT
    return WildEncounterOutcomeT.DEFEAT


async def conclude_actual_encounter(
    sess: AsyncSession,
    *,
    registry: battle_play.BattleSessionRegistry,
    session: battle_play.ActiveBattle,
    trainer_id: TrainerIdT,
    outcome: WildEncounterOutcomeT | None = None,
) -> ActualEncounterConclusion:
    """Finish battle progression and record the Wild Pool encounter outcome."""
    progression = None
    if session.engine.battle.concluded:
        progression = await battle_play.finish_battle(
            sess,
            session=session,
            registry=registry,
        )
    resolved_outcome = outcome or encounter_outcome_from_battle(session)
    await wild_encounter.record_wild_encounter_outcome(
        sess,
        trainer_id=trainer_id,
        vibemon_id=session.wild_vibemon_id,
        outcome=resolved_outcome,
    )
    return ActualEncounterConclusion(outcome=resolved_outcome, progression=progression)


async def record_encounter_outcome_only(
    sess: AsyncSession,
    *,
    trainer_id: TrainerIdT,
    vibemon_id: uuid.UUID,
    outcome: WildEncounterOutcomeT,
) -> None:
    await wild_encounter.record_wild_encounter_outcome(
        sess,
        trainer_id=trainer_id,
        vibemon_id=vibemon_id,
        outcome=outcome,
    )
