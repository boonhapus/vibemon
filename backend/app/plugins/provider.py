from typing import ClassVar
import abc

from app import schema


class VibeProvider(abc.ABC):
    """
    Base interface for provider plugins.

    Subclasses only need to:
    - set `name` class attribute
    - implement `synthesize()` to translate raw API data to Affinity components
    - optionally override `teardown()` when managing resources

    Use optional helpers from `app.plugins.helpers`:
    - normalize(value, low, high) -> float
    - select_elements(scores, primary_min, secondary_ratio) -> tuple
    - sample_move_pool(weighted_moves, pool_size) -> list[Move]
    - apply_type_affinity_weights(move_weights, elements) -> dict
    """

    name: ClassVar[str]
    """Stable provider identifier (persisted in `Affinity.provider_id`)."""

    @abc.abstractmethod
    async def synthesize(self, ctx: schema.BirthContext) -> schema.Affinity:
        """
        Translate raw API data to Affinity components.

        Use ctx.geo_coords, ctx.timestamp, ctx.providers as needed.
        Return a complete Affinity with identity, moves, intensity, and visual_notes.
        """

    async def teardown(self) -> None:
        """Release provider-owned resources. Override only when needed."""
