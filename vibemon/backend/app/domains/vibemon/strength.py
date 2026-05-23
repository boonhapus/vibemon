"""Battle-readiness formulas for member and party strength."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

PARTY_MAX_BONUS_RATIO = 0.25
PARTY_TOTAL_BONUS_RATIO = 0.10


class StrengthIdentity(Protocol):
    @property
    def base_hp(self) -> int: ...

    @property
    def base_attack(self) -> int: ...

    @property
    def base_defense(self) -> int: ...

    @property
    def base_sp_attack(self) -> int: ...

    @property
    def base_sp_defense(self) -> int: ...

    @property
    def base_speed(self) -> int: ...


class StrengthMember(Protocol):
    @property
    def level(self) -> int: ...

    @property
    def identity(self) -> StrengthIdentity | None: ...


def member_strength(member: StrengthMember) -> float:
    identity = member.identity
    assert identity is not None
    level = max(member.level, 1)
    hp = int(((2 * identity.base_hp * level) / 100) + 10 + level)
    attack = int(((2 * identity.base_attack * level) / 100) + 5)
    defense = int(((2 * identity.base_defense * level) / 100) + 5)
    sp_attack = int(((2 * identity.base_sp_attack * level) / 100) + 5)
    sp_defense = int(((2 * identity.base_sp_defense * level) / 100) + 5)
    speed = int(((2 * identity.base_speed * level) / 100) + 5)
    return float(hp + attack + defense + sp_attack + sp_defense + speed)


def party_strength(strengths: Iterable[float]) -> float:
    values = [max(float(value), 0.0) for value in strengths]
    if not values:
        return 0.0
    total = sum(values)
    avg = total / len(values)
    return avg + (max(values) * PARTY_MAX_BONUS_RATIO) + (total * PARTY_TOTAL_BONUS_RATIO)
