from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.context import GenerationContext, SourceData


class VibemonProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    async def fetch(self, context: GenerationContext) -> SourceData: ...
