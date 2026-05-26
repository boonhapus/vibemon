"""Vibemon identity schema and derived battle profile."""

from __future__ import annotations

from typing import Literal, cast
import datetime as dt

import pydantic

from app.core.schema import Schema
from app.core.time import resolve_clock
from app.domains.vibemon import types


class Identity(Schema):
    name: str
    visual_notes: str | None = None
    provider_visual_notes: str | None = None
    elements: types.IdentityElementsT

    # fmt: off
    base_hp: int         = pydantic.Field(default=70, ge= 1, le=255, json_schema_extra={"min":  1, "med": 70, "max": 255})  # noqa: E501
    base_attack: int     = pydantic.Field(default=75, ge= 5, le=190, json_schema_extra={"min":  5, "med": 75, "max": 190})  # noqa: E501
    base_defense: int    = pydantic.Field(default=70, ge= 5, le=230, json_schema_extra={"min":  5, "med": 70, "max": 230})  # noqa: E501
    base_sp_attack: int  = pydantic.Field(default=70, ge=10, le=194, json_schema_extra={"min": 10, "med": 70, "max": 194})  # noqa: E501
    base_sp_defense: int = pydantic.Field(default=70, ge=20, le=230, json_schema_extra={"min": 20, "med": 70, "max": 230})  # noqa: E501
    base_speed: int      = pydantic.Field(default=70, ge= 5, le=200, json_schema_extra={"min":  5, "med": 70, "max": 200})  # noqa: E501
    # fmt: on

    evo_seed: types.EvolutionStageT = types.EvolutionStageT.BASE
    is_radiant: bool = False
    generation: int = 0
    generated_at: dt.datetime = pydantic.Field(default_factory=resolve_clock)

    @classmethod
    def _stat_info(cls, name: types.BaseStatNameT, type: Literal["min", "med", "max"] = "med") -> int | None:
        if (field := cls.model_fields.get(f"base_{name}")) and field.json_schema_extra:
            assert isinstance(field.json_schema_extra, dict), "json_schema_extra must be a dict."
            return cast(int, field.json_schema_extra[type])
        return None

    @property
    def bst(self) -> int:
        return (
            self.base_hp
            + self.base_attack
            + self.base_defense
            + self.base_sp_attack
            + self.base_sp_defense
            + self.base_speed
        )

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
        hp = self.base_hp
        atk = self.base_attack
        sp_atk = self.base_sp_attack
        defense = self.base_defense
        sp_def = self.base_sp_defense
        speed = self.base_speed

        phys_ehp = hp * defense
        spec_ehp = hp * sp_def
        avg_ehp = (phys_ehp + spec_ehp) / 2
        best_offense = max(atk, sp_atk)

        is_very_fast = speed >= 110
        is_fast = speed >= 95
        is_slow = speed < 65

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
