from __future__ import annotations

from typing import Annotated, Literal

import pydantic

from app import types
from app.domain.birth import FrozenSchema


class DamageModifier(FrozenSchema):
    """A fixed-point damage modifier."""

    key: str
    numerator: int
    display: float
    source: str | None = None


class DamageStep(FrozenSchema):
    """One ordered damage calculation step."""

    key: str
    modifiers: tuple[DamageModifier, ...]
    rounding: Literal["floor", "round_half_down", "round_half_up"]
    damage_after: int


class DamageResult(FrozenSchema):
    """Auditable result of the damage pipeline."""

    damage: int
    is_crit: bool
    random_roll: int | None
    effectiveness: float
    base_damage: int
    steps: tuple[DamageStep, ...]
    blocked_reason: Literal["type_immune", "ability_immune", "move_failed"] | None = None


class MoveUsedEvent(FrozenSchema):
    """A move was used."""

    kind: Literal["move_used"] = "move_used"
    user: str
    move: str
    targets: tuple[str, ...]


class MoveMissedEvent(FrozenSchema):
    """A move missed a target."""

    kind: Literal["move_missed"] = "move_missed"
    user: str
    move: str
    target: str


class MoveFailedEvent(FrozenSchema):
    """A move failed before hitting."""

    kind: Literal["move_failed"] = "move_failed"
    user: str
    move: str | None = None
    reason: str | None = None


class DamageEvent(FrozenSchema):
    """Damage was dealt."""

    kind: Literal["damage"] = "damage"
    source: str
    target: str
    move: str | None = None
    amount: int
    hp_after: int
    is_crit: bool
    effectiveness: float
    modifiers: tuple[DamageModifier, ...] = ()


class FaintEvent(FrozenSchema):
    """A target fainted."""

    kind: Literal["faint"] = "faint"
    target: str


class StatusInflictedEvent(FrozenSchema):
    """A status condition was inflicted."""

    kind: Literal["status_inflicted"] = "status_inflicted"
    source: str | None
    target: str
    status: types.StatusConditionT


class StatusDamageEvent(FrozenSchema):
    """Residual status damage was dealt."""

    kind: Literal["status_damage"] = "status_damage"
    target: str
    amount: int
    hp_after: int


class StatusMessageEvent(FrozenSchema):
    """A status or volatile condition produced a message."""

    kind: Literal["status_message"] = "status_message"
    target: str
    message_key: str


class StatChangeEvent(FrozenSchema):
    """Stat stages changed."""

    kind: Literal["stat_change"] = "stat_change"
    source: str | None
    target: str
    changes: dict[types.StatStageNameT, int]


class HealEvent(FrozenSchema):
    """HP was restored."""

    kind: Literal["heal"] = "heal"
    source: str | None
    target: str
    amount: int
    hp_after: int


class WeatherSetEvent(FrozenSchema):
    """Field weather changed."""

    kind: Literal["weather_set"] = "weather_set"
    source: str | None
    weather: types.WeatherT
    turns: int


type TurnEvent = Annotated[
    MoveUsedEvent
    | MoveMissedEvent
    | MoveFailedEvent
    | DamageEvent
    | FaintEvent
    | StatusInflictedEvent
    | StatusDamageEvent
    | StatusMessageEvent
    | StatChangeEvent
    | HealEvent
    | WeatherSetEvent,
    pydantic.Discriminator("kind"),
]
