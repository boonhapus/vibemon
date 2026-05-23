"""Move-domain schemas and declarative move behavior."""

from __future__ import annotations

from typing import Annotated, Literal
import re

import pydantic

from app.core.schema import FrozenSchema
from app.domains.move.types import MoveCategoryT, MoveTargetT, StatStageNameT, StatusConditionT, VibemonTypeT, WeatherT

type EffectTarget = Literal["self", "target", "all_targets", "side", "opposing_side"]

_MOVE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*\.[a-z0-9]+(?:_[a-z0-9]+)*$")
_CANONICAL_NAME_TOKEN_PATTERN = re.compile(r"[0-9a-z]+")


class StatusInflict(FrozenSchema):
    kind: Literal["status"] = "status"
    target: EffectTarget = "target"
    status: StatusConditionT


class StatChange(FrozenSchema):
    kind: Literal["stat"] = "stat"
    target: EffectTarget = "target"
    changes: dict[StatStageNameT, int]


class Drain(FrozenSchema):
    kind: Literal["drain"] = "drain"
    ratio: float


class Recoil(FrozenSchema):
    kind: Literal["recoil"] = "recoil"
    ratio: float


class WeatherSet(FrozenSchema):
    kind: Literal["weather"] = "weather"
    weather: WeatherT
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
    weather: WeatherT
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


class Move(FrozenSchema):
    id: str
    name: str
    flavor_text: str
    type: VibemonTypeT
    category: MoveCategoryT
    power: int | None = None
    accuracy: float | None = 1.0
    pp: int = 10
    priority: Annotated[int, pydantic.Field(ge=-7, le=7)] = 0
    effects: tuple[EffectGroup, ...] = ()
    behavior: MoveBehavior = pydantic.Field(default_factory=MoveBehavior)
    target: MoveTargetT = MoveTargetT.SINGLE
    level_requirement: int = 1

    @pydantic.model_validator(mode="after")
    def _set_or_validate_id(self) -> Move:
        validate_move_id(self.id)
        return self

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return NotImplemented
        return self.id == other.id

    @property
    def canonical_name(self) -> str:
        return canonicalize_move_name(self.name)


def validate_move_id(move_id: str) -> None:
    """Require the canonical `<provider_slug>.<move_slug>` move identity format."""
    if not _MOVE_ID_PATTERN.fullmatch(move_id):
        raise ValueError("Move id must use '<provider_slug>.<move_slug>' with lowercase snake-case slugs.")


def canonicalize_move_name(name: str) -> str:
    """Normalize display names for global uniqueness checks."""
    tokens = _CANONICAL_NAME_TOKEN_PATTERN.findall(name.strip().casefold())
    if not tokens:
        raise ValueError("Move name must contain at least one alphanumeric character.")
    return " ".join(tokens)
