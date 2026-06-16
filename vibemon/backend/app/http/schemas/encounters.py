"""HTTP schemas for Actual Encounter routes."""

import uuid

from app.core.schema import Schema
from app.domains.encounter.types import WildEncounterOutcomeT
from app.domains.encounter.wild_encounter import EncounterSelection
from app.domains.vibemon.progression import engine as progression_engine
from app.http import battle_read


class EncounterStartBody(Schema):
    hero_vibemon_id: uuid.UUID
    latitude: float | None = None
    longitude: float | None = None
    desired_supply: int = 12


class EncounterStartResponse(Schema):
    selection: EncounterSelection
    battle: battle_read.BattleStateRead


class EncounterTurnBody(Schema):
    move_name: str


class EncounterConcludeBody(Schema):
    outcome: WildEncounterOutcomeT | None = None


class EncounterConcludeResponse(Schema):
    outcome: WildEncounterOutcomeT
    progression: progression_engine.BattleProgressionResult | None = None
