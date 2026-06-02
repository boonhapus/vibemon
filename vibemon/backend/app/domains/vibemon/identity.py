"""Vibemon identity schema and derived battle profile."""

from typing import Literal, cast
import datetime as dt

import pydantic

from app.core.schema import Schema
from app.core.time import resolve_clock
from app.domains.vibemon import types


class BaseStats(Schema):
    """Scaled base stats ready to unpack into ``Identity``."""

    hp: int = pydantic.Field(default=70, ge=1, le=255, json_schema_extra={"min": 1, "med": 70, "max": 255})
    attack: int = pydantic.Field(default=75, ge=5, le=190, json_schema_extra={"min": 5, "med": 75, "max": 190})
    defense: int = pydantic.Field(default=70, ge=5, le=230, json_schema_extra={"min": 5, "med": 70, "max": 230})
    sp_attack: int = pydantic.Field(default=70, ge=10, le=194, json_schema_extra={"min": 10, "med": 70, "max": 194})
    sp_defense: int = pydantic.Field(default=70, ge=20, le=230, json_schema_extra={"min": 20, "med": 70, "max": 230})
    speed: int = pydantic.Field(default=70, ge=5, le=200, json_schema_extra={"min": 5, "med": 70, "max": 200})

    @property
    def total(self) -> int:
        """Sum of all base stats, the canonical power level."""
        return self.hp + self.attack + self.defense + self.sp_attack + self.sp_defense + self.speed

    @classmethod
    def _stat_info(cls, name: types.BaseStatNameT, type: Literal["min", "med", "max"] = "med") -> int | None:
        if (field := cls.model_fields.get(name)) and field.json_schema_extra:
            assert isinstance(field.json_schema_extra, dict), "json_schema_extra must be a dict."
            return cast(int, field.json_schema_extra[type])
        return None


class Identity(Schema):
    name: str
    visual_notes: str | None = None
    provider_visual_notes: str | None = None
    elements: types.IdentityElementsT
    base: BaseStats
    evo_seed: types.EvolutionStageT = types.EvolutionStageT.BASE
    is_radiant: bool = False
    generation: int = 0
    generated_at: dt.datetime = pydantic.Field(default_factory=resolve_clock)

    @property
    def bst(self) -> int:
        """Sum of all base stats, the canonical power level."""
        return self.base.total

    @property
    def tier(self) -> types.TierT:
        match self.bst:
            case b if b < 400:
                return types.TierT.RUNT
            case b if b < 500:
                return types.TierT.MID
            case b if b < 570:
                return types.TierT.SOLID
            case b if b < 670:
                return types.TierT.APEX
            case _:
                return types.TierT.MYTHIC

    @property
    def battle_role(self) -> types.BattleRole:
        phys_ehp = self.base.hp * self.base.defense
        spec_ehp = self.base.hp * self.base.sp_defense
        avg_ehp = (phys_ehp + spec_ehp) / 2
        best_offense = max(self.base.attack, self.base.sp_attack)

        is_very_fast = self.base.speed >= 110
        is_fast = self.base.speed >= 95
        is_slow = self.base.speed < 65

        is_elite_off = best_offense >= 120
        is_strong_off = best_offense >= 100
        is_decent_off = best_offense >= 95

        is_phys_wall = phys_ehp >= 8000
        is_spec_wall = spec_ehp >= 8000
        is_any_wall = is_phys_wall or is_spec_wall
        is_mixed_bulk = phys_ehp >= 6000 and spec_ehp >= 6000
        is_frail = avg_ehp < 5000

        match True:
            case _ if is_fast and is_strong_off and is_frail:
                return types.BattleRole.OFFENSIVE_GLASS_CANNON
            case _ if is_slow and is_elite_off:
                return types.BattleRole.OFFENSIVE_WALLBREAKER
            case _ if is_fast and is_strong_off:
                return types.BattleRole.OFFENSIVE_SWEEPER
            case _ if is_very_fast and is_decent_off:
                return types.BattleRole.OFFENSIVE_REVENGE_KILLER
            case _ if is_mixed_bulk and is_decent_off:
                return types.BattleRole.DEFENSIVE_TANK
            case _ if is_any_wall and not is_decent_off:
                return types.BattleRole.DEFENSIVE_WALL
            case _ if is_mixed_bulk and is_slow:
                return types.BattleRole.DEFENSIVE_STALLER
            case _ if is_fast and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_PIVOT
            case _ if best_offense < 80 and avg_ehp >= 5000:
                return types.BattleRole.UTILITY_CLERIC
            case _:
                return types.BattleRole.UTILITY
