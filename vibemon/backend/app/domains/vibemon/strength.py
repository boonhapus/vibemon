"""Battle-readiness formulas for member and crew strength."""

from collections.abc import Iterable
from typing import Protocol

from app.domains.vibemon.identity import BaseStats

CREW_MAX_BONUS_RATIO = 0.25
CREW_TOTAL_BONUS_RATIO = 0.10


class StrengthIdentity(Protocol):
    @property
    def base(self) -> BaseStats: ...


class StrengthMember(Protocol):
    @property
    def level(self) -> int: ...

    @property
    def identity(self) -> StrengthIdentity | None: ...


def member_strength(member: StrengthMember) -> float:
    identity = member.identity
    assert identity is not None
    level = max(member.level, 1)
    base = identity.base
    hp = int(((2 * base.hp * level) / 100) + 10 + level)
    attack = int(((2 * base.attack * level) / 100) + 5)
    defense = int(((2 * base.defense * level) / 100) + 5)
    sp_attack = int(((2 * base.sp_attack * level) / 100) + 5)
    sp_defense = int(((2 * base.sp_defense * level) / 100) + 5)
    speed = int(((2 * base.speed * level) / 100) + 5)
    return float(hp + attack + defense + sp_attack + sp_defense + speed)


def crew_strength(strengths: Iterable[float]) -> float:
    values = [max(float(value), 0.0) for value in strengths]
    if not values:
        return 0.0
    total = sum(values)
    avg = total / len(values)
    return avg + (max(values) * CREW_MAX_BONUS_RATIO) + (total * CREW_TOTAL_BONUS_RATIO)
