from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import schema


class Base:
    """The interface for all providers."""

    async def generate(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Generate the Vibemon stats based on the provider's data."""
        raise NotImplementedError("Override .generate() in your subclass.")