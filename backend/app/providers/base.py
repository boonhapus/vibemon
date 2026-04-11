from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from attrs import define, field


@define
class SourceData:
    """Normalised output from any data provider."""

    hp_factor: Optional[float] = None
    attack_factor: Optional[float] = None
    defense_factor: Optional[float] = None
    sp_attack_factor: Optional[float] = None
    sp_defense_factor: Optional[float] = None
    speed_factor: Optional[float] = None
    element_votes: list[tuple[str, float]] = field(factory=list)
    hue_primary: Optional[float] = None
    hue_secondary: Optional[float] = None
    luminosity: Optional[float] = None
    flavour_text: Optional[str] = None
    raw: dict = field(factory=dict)


@define
class GenerationContext:
    user_id: str
    timestamp: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    auth_tokens: dict[str, str] = field(factory=dict)


class VibemonProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    async def fetch(self, context: GenerationContext) -> SourceData: ...
