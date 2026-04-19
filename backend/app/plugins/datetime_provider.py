import structlog
from app.schema import GenerationContext, SourceData
from app.plugins.protocol import DataProvider

log = structlog.get_logger(__name__)


class DatetimeProvider(DataProvider):
    source_id = "datetime"

    async def fetch(self, ctx: GenerationContext) -> SourceData:
        log.debug(
            "datetime_provider_fetch",
            ts=ctx.timestamp,
            lat=ctx.latitude,
            lon=ctx.longitude,
        )
        ts = ctx.timestamp
        hp_factor = 0.3 + 0.4 * ((ts.hour % 24) / 24.0)
        attack_factor = 0.3 + 0.4 * ((ts.weekday() + 1) / 7.0)
        defense_factor = 0.3 + 0.4 * (abs(ctx.latitude) / 90.0)
        sp_attack_factor = 0.3 + 0.4 * ((ts.month % 12) / 12.0)
        sp_defense_factor = 0.3 + 0.4 * ((abs(ctx.longitude) % 180) / 180.0)
        speed_factor = 0.3 + 0.4 * ((ts.second % 60) / 60.0)
        hue = 35.0 + (ts.hour / 24.0) * 20.0
        return SourceData(
            hp_factor=hp_factor,
            attack_factor=attack_factor,
            defense_factor=defense_factor,
            sp_attack_factor=sp_attack_factor,
            sp_defense_factor=sp_defense_factor,
            speed_factor=speed_factor,
            element_votes=[
                ("Fire", hp_factor),
                ("Water", 1.0 - hp_factor),
                ("Grass", attack_factor),
                ("Electric", defense_factor),
                ("Ice", sp_attack_factor),
                ("Normal", sp_defense_factor),
            ],
            hue_primary=hue,
            luminosity=0.5 + (ts.minute / 60.0) * 0.2,
            flavour_text=f"Captured at {ctx.latitude:.2f}, {ctx.longitude:.2f}",
            raw={"timestamp": ctx.timestamp.isoformat(), "provider": "datetime"},
        )
