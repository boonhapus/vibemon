import random

from app.plugins.base import VibeProvider
from app import schema

from . import element_list, move_list, utils, weather


class ClimateProvider(VibeProvider):
    """A data source which fetches the current weather."""

    __provider_name__ = "climate"

    def __init__(self) -> None:
        self.client = weather.WeatherAPIClient()

    async def teardown(self) -> None:
        """Clean up provider-owned resources."""
        await self.client.close()

    async def generate(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Generate the Vibemon stats based on the provider's data."""
        r = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        d = r.json()

        dummy = schema.Identity.null_identity()

        ident = schema.Identity(
            name="UNNAMED",
            elements=element_list.infer_elements(d),
            base_hp=utils.jitter(dummy.base_hp),
            base_attack=utils.jitter(dummy.base_attack),
            base_defense=utils.jitter(dummy.base_defense),
            base_sp_attack=utils.jitter(dummy.base_sp_attack),
            base_sp_defense=utils.jitter(dummy.base_sp_defense),
            base_speed=utils.jitter(dummy.base_speed),
        )

        affinity = schema.Affinity(
            identity=ident,
            visual_notes=d["current"]["condition"]["text"],
            intensity=1.0,
            provider_id=self.__provider_name__,
            moves=random.sample(move_list.MOVES, k=10),
        )

        return affinity
