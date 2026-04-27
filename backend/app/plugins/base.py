from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import schema


class VibeProvider:
    """Interface for plugins that translate external data into Vibemon affinities."""

    async def generate(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Generate an affinity from the provider's data source."""
        raise NotImplementedError("Override .generate() in your subclass.")

    async def teardown(self) -> None:
        """Clean up provider-owned resources."""
        raise NotImplementedError("Override .teardown() in your subclass.")
