from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar
import enum

from app import schema
from app.battle import events


class HookPriority(enum.IntEnum):
    """Standard hook priority bands."""

    EARLY = -100
    NORMAL = 0
    LATE = 100


class RegisteredHook(schema._Static):
    """A hook with explicit ordering metadata."""

    priority: int = HookPriority.NORMAL
    source: str
    hook: Callable


T = TypeVar("T")


class HookRegistry:
    """Typed first-party hook registry."""

    def __init__(self) -> None:
        self._hooks: dict[type[object], list[RegisteredHook]] = {}

    def register(self, protocol: type[T], hook: T, *, source: str, priority: int = 0) -> None:
        self._hooks.setdefault(protocol, []).append(RegisteredHook(priority=priority, source=source, hook=hook))

    def get(self, protocol: type[T]) -> tuple[T, ...]:
        registered = sorted(self._hooks.get(protocol, ()), key=lambda item: (item.priority, item.source))
        return tuple(item.hook for item in registered)


class DamageModifierHook(Protocol):
    """Hook that contributes modifiers to one damage phase."""

    def __call__(self, phase: str, ctx: object, use: object, target: object) -> tuple[events.DamageModifier, ...]: ...


class EndOfTurnHook(Protocol):
    """Hook run during end-of-turn maintenance."""

    def __call__(self, ctx: object) -> None: ...


class AccuracyHook(Protocol):
    """Hook that can modify or block hit checks."""

    def __call__(self, ctx: object, use: object, target: object) -> bool | None: ...
