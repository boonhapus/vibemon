from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schema import GenerationContext, SourceData


class DataProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str: ...

    @abstractmethod
    async def fetch(self, ctx: "GenerationContext") -> "SourceData": ...
