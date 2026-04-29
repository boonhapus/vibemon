from typing import ClassVar, final
import abc

from app.plugins.engine import IdentityEngine, Ruleset, Vocabulary
from app import schema


class VibeProvider(abc.ABC):
    """
    Base interface for provider plugins.

    Subclasses only need to:
    - set `name` and `ruleset` class attributes
    - implement `make_vocabulary()`
    - optionally override `teardown()` when managing resources
    """

    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""

    ruleset: ClassVar[Ruleset]
    """Ruleset used by the identity engine for this provider."""

    @abc.abstractmethod
    async def make_vocabulary(self, ctx: schema.BirthContext) -> Vocabulary:
        """Return normalized provider data for a single birth context."""

    @final
    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Run the shared provider -> engine -> affinity pipeline."""
        if not self.name:
            raise ValueError("Provider must define a non-empty `name` class attribute.")

        vocabulary = await self.make_vocabulary(ctx)
        engine = IdentityEngine(vocabulary=vocabulary, ruleset=self.ruleset)

        return schema.Affinity(
            identity=engine.synthesize_identity(),
            visual_notes=engine.generate_visual_note(),
            intensity=engine.get_intensity_value(),
            provider_id=self.name,
            moves=engine.synthesize_moves(),
        )

    async def teardown(self) -> None:
        """Release provider-owned resources. Override only when needed."""
