import random

from app.plugins.base import Base
from app import schema

from . import element_list, move_list, utils, weather


class ClimateProvider(Base):
    """A data source which fetches the current weather."""
    __provider_name__ = "climate"

    def __init__(self):
        self.client = weather.WeatherAPIClient()

    async def teardown(self) -> None:
        await self.client.close()

    async def generate(self, ctx: schema.BirthContext) -> schema.Affinity:
        """Generate the Vibemon stats based on the provider's data."""
        r = await self.client.current_weather(latitude=ctx.geo_coords[0], longitude=ctx.geo_coords[1])
        d = r.json()

        affinity = schema.Affinity(
            intensity=1.0,
            description=d["current"]["condition"]["text"],
            elements=element_list.infer_elements(d),
            moves=random.sample(move_list.MOVES, k=10),
        )

        # APPLY JITTER SO IT'S NOT ALWAYS THE SAME STATS.
        for base_stat in ("base_hp", "base_attack", "base_defense", "base_sp_attack", "base_sp_defense", "base_speed"):
            new_value = utils.jitter(getattr(affinity, base_stat))
            setattr(affinity, base_stat, new_value)

        return affinity
