"""Move-domain schemas and declarative move behavior."""

from __future__ import annotations

from typing import Annotated, Literal

import pydantic

from app import types, validators
from app.domain.birth import FrozenSchema

type EffectTarget = Literal["self", "target", "all_targets", "side", "opposing_side"]


class StatusInflict(FrozenSchema):
    kind: Literal["status"] = "status"
    target: EffectTarget = "target"
    status: types.StatusConditionT


class StatChange(FrozenSchema):
    kind: Literal["stat"] = "stat"
    target: EffectTarget = "target"
    changes: dict[types.StatStageNameT, int]


class Drain(FrozenSchema):
    kind: Literal["drain"] = "drain"
    ratio: float


class Recoil(FrozenSchema):
    kind: Literal["recoil"] = "recoil"
    ratio: float


class WeatherSet(FrozenSchema):
    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    turns: int


class Heal(FrozenSchema):
    kind: Literal["heal"] = "heal"
    target: EffectTarget = "self"
    ratio: float


type Effect = Annotated[
    StatusInflict | StatChange | Drain | Recoil | WeatherSet | Heal,
    pydantic.Discriminator("kind"),
]


class EffectGroup(FrozenSchema):
    chance: float = 1.0
    trigger: Literal["on_hit", "on_use", "after_damage"] = "on_hit"
    effects: tuple[Effect, ...] = ()


class ConditionalOverride(FrozenSchema):
    valid: bool | None = None
    priority_delta: int = 0
    accuracy_override: float | None = None
    power_multiplier: float | None = None
    flavor_key: str | None = None


class IfOpponentAttacking(FrozenSchema):
    kind: Literal["opponent_attacking"] = "opponent_attacking"
    on_match: ConditionalOverride
    on_miss: ConditionalOverride | None = None


class IfWeather(FrozenSchema):
    kind: Literal["weather"] = "weather"
    weather: types.WeatherT
    on_match: ConditionalOverride


class IfHpBelow(FrozenSchema):
    kind: Literal["hp_below"] = "hp_below"
    threshold: float
    on_match: ConditionalOverride


class RandomPower(FrozenSchema):
    kind: Literal["random_power"] = "random_power"
    buckets: tuple[tuple[float, int], ...]


type Condition = Annotated[
    IfOpponentAttacking | IfWeather | IfHpBelow | RandomPower,
    pydantic.Discriminator("kind"),
]


class MoveBehavior(FrozenSchema):
    conditions: tuple[Condition, ...] = ()
    script_id: str | None = None


class Move(FrozenSchema):
    name: str
    flavor_text: str
    type: types.VibemonTypeT
    category: types.MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0
    pp: int = 10
    priority: Annotated[int, validators.ensure_between_abs_7] = 0
    effects: tuple[EffectGroup, ...] = ()
    behavior: MoveBehavior = pydantic.Field(default_factory=MoveBehavior)
    target: types.MoveTargetT = types.MoveTargetT.SINGLE
    level_requirement: int = 1

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return self.name == other.name
