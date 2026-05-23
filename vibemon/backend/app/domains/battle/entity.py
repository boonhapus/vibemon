from __future__ import annotations

from typing import Any, Self, cast

import pydantic

from app.core.schema import Schema
from app.domains.battle import actions as action_models
from app.domains.battle import events as event_models
from app.domains.move.entity import Move
from app.domains.move.types import StatusConditionT, WeatherT
from app.domains.trainer.entity import Trainer
from app.domains.vibemon.entity import Vibemon


class FieldWeather(Schema):
    """Battle-scoped weather state."""

    kind: WeatherT = WeatherT.CLEAR
    turns_remaining: int = 0


class FieldState(Schema):
    """Battle field state."""

    weather: FieldWeather = pydantic.Field(default_factory=FieldWeather)


class BattleMove(Move, frozen=False, validate_assignment=True):
    """Transient battle state layered on top of move content."""

    pp_current: int = -1
    priority: int = 0
    crit_ratio: int = 0

    @pydantic.model_validator(mode="after")
    def _set_current_pp_if_not_default(self) -> Self:
        if self.pp_current == -1:
            self.pp_current = self.pp
        return self


class StatStages(Schema):
    """Stat stage modifiers accumulated during battle."""

    attack: int = 0
    defense: int = 0
    sp_attack: int = 0
    sp_defense: int = 0
    speed: int = 0
    accuracy: int = 0
    evasion: int = 0


class BattleVibemon(Vibemon, frozen=False, validate_assignment=True):
    """Transient battle state layered on top of a Vibemon."""

    current_hp: int = 0
    battle_moves: list[BattleMove] = pydantic.Field(default_factory=list)
    status: StatusConditionT = StatusConditionT.NONE
    stat_stages: StatStages = pydantic.Field(default_factory=StatStages)
    crit_stage: int = 0

    is_flinched: bool = False
    is_confused: bool = False
    confusion_turns: int = 0
    bad_poison_counter: int = 0
    sleep_turns_remaining: int = 0
    is_seeded: bool = False
    taunt_turns: int = 0
    bound_turns: int = 0

    @pydantic.model_validator(mode="after")
    def _apply_battle_defaults(self) -> Self:
        if "current_hp" not in self.model_fields_set:
            self.current_hp = self.hp
        if not self.battle_moves:
            self.battle_moves = [BattleMove(**move.model_dump()) for move in self.moves]
        return self

    @property
    def max_hp(self) -> int:
        return self.hp

    @property
    def is_fainted(self) -> bool:
        return self.current_hp <= 0


class BattleTrainer(Trainer, frozen=False, validate_assignment=True):
    """Transient battle state layered on top of a Trainer."""

    active_index: int = 0
    team: list[Vibemon] = pydantic.Field(default_factory=list)

    @property
    def active_vibemon(self) -> BattleVibemon:
        return cast(BattleVibemon, self.team[self.active_index])

    @property
    def has_vibemon_remaining(self) -> bool:
        return any(not cast(BattleVibemon, p).is_fainted for p in self.team)


class TurnRecord(Schema):
    """A submitted turn and its emitted events."""

    turn_number: int
    actions: list[action_models.BattleAction] = pydantic.Field(default_factory=list)
    events: list[event_models.TurnEvent] = pydantic.Field(default_factory=list)


class Battle(Schema):
    """The persistent mutable state of a battle."""

    trainer_a: BattleTrainer
    trainer_b: BattleTrainer
    field: FieldState = pydantic.Field(default_factory=FieldState)
    turn_number: int = 1
    turn_history: list[TurnRecord] = pydantic.Field(default_factory=list)
    winner: BattleTrainer | None = None

    @property
    def concluded(self) -> bool:
        return self.winner is not None

    def to_json(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
