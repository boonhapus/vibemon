"""BiomeProvider: place-of-birth affinity from land cover, elevation, water, and solar phase."""

from typing import ClassVar
import asyncio
import collections

import structlog

from app.core.math import clamp
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import Identity
from app.providers import catalog_schema as catalog
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider
from app.providers.biome import schema as biome_schema
from app.providers.catalog_support import GEOLOCATION_REQUIREMENT
from app.providers.helpers import Signal, filter_element_types, pick_starter_moves

from . import const
from .raster.elevation import api as elevation_api
from .raster.worldcover import api as worldcover_api
from .water.overpass import api as overpass_api

_LOGGER = structlog.get_logger(__name__)


class BiomeProvider(VibeProvider[biome_schema.BiomePayload]):
    """
    A Vibemon is born from the ground beneath its birthplace.

    One raised on London pavement reads differently from one hatched in Amazon
    canopy or Sahara scrub - linoleum suburbs, red-clay back roads, and river
    mud all leave a different print underfoot.
    """

    name = "biome"
    payload_type = biome_schema.BiomePayload

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "grassland, cropland, or suburban open land"),
        (VibemonTypeT.FIRE, "bare sparse vegetation and arid scrub"),
        (VibemonTypeT.WATER, "permanent water, wetlands, or proximity to rivers and coast"),
        (VibemonTypeT.GRASS, "tree cover, grassland, cropland, and mangroves"),
        (VibemonTypeT.ICE, "snow and ice cover or high cold elevation"),
        (VibemonTypeT.FLYING, "open grassland and high-elevation exposure"),
        (VibemonTypeT.FIGHTING, "shrubland badlands and rugged sparse ground"),
        (VibemonTypeT.POISON, "wetlands, built-up industry, and stagnant water"),
        (VibemonTypeT.GROUND, "bare sparse land and dry shrub"),
        (VibemonTypeT.BUG, "tree cover, cropland, and mangrove understory"),
        (VibemonTypeT.ROCK, "bare sparse ground, moss/lichen, and high elevation"),
        (VibemonTypeT.GHOST, "tree cover shade and built-up historical footprint"),
        (VibemonTypeT.DRAGON, "high elevation wilderness and isolated terrain"),
        (VibemonTypeT.ELECTRIC, "built-up urban fabric"),
        (VibemonTypeT.DARK, "built-up districts and nocturnal solar phase"),
        (VibemonTypeT.STEEL, "built-up industrial clusters"),
        (VibemonTypeT.FAIRY, "moss/lichen groves and dawn or dusk solar phase"),
        (VibemonTypeT.PSYCHIC, "dawn stillness in forest or open land"),
    ]

    display_label = "GROUND"
    tagline = "Dirt, pavement, and what is underfoot."
    data_sources = (
        catalog.DataSourceInfo(name="ESA WorldCover", description="Land-cover classification underfoot."),
        catalog.DataSourceInfo(name="Open-Meteo", description="Elevation at trainer coordinates."),
        catalog.DataSourceInfo(name="OpenStreetMap", description="Water proximity via Overpass queries."),
    )
    requirements = (GEOLOCATION_REQUIREMENT,)

    def __init__(self) -> None:
        self.worldcover = worldcover_api.TerrascopeWorldCoverClient()
        self.elevation = elevation_api.OpenMeteoElevationClient()
        self.water = overpass_api.OverpassWaterClient()

    # ── INTERNAL HELPERS ──────────────────────────────────────────────────────────────

    @classmethod
    def balance_for_bst(
        cls,
        *,
        land_cover: const.WorldCoverClassT,
        built_up_fraction: float,
        elevation_m: float,
    ) -> providers_schema.BaseStatCenters:
        archetype = land_cover.profile.stat_archetype
        urbanity = clamp(built_up_fraction, minimum=0.0, maximum=1.0)
        elevation_signal = Signal(
            name="elevat",
            attr="elevation_m",
            raw=elevation_m,
            min=-430.0,
            med=350.0,
            max=5100.0,
        ).center

        hp = const.STAT_TIER_CENTER[archetype["hp"]]
        attack = const.STAT_TIER_CENTER[archetype["attack"]]
        defense = const.STAT_TIER_CENTER[archetype["defense"]]
        sp_attack = const.STAT_TIER_CENTER[archetype["sp_attack"]]
        sp_defense = const.STAT_TIER_CENTER[archetype["sp_defense"]]
        speed = const.STAT_TIER_CENTER[archetype["speed"]]

        return providers_schema.BaseStatCenters(
            hp=clamp(hp - 0.08 * urbanity, minimum=0.0, maximum=1.0),
            attack=attack,
            defense=clamp(defense + 0.08 * elevation_signal, minimum=0.0, maximum=1.0),
            sp_attack=clamp(sp_attack + 0.08 * urbanity, minimum=0.0, maximum=1.0),
            sp_defense=clamp(sp_defense - 0.08 * urbanity, minimum=0.0, maximum=1.0),
            speed=clamp(speed + 0.08 * urbanity - 0.08 * elevation_signal, minimum=0.0, maximum=1.0),
        )

    def stat_centers(self, payload: biome_schema.BiomePayload) -> providers_schema.BaseStatCenters:
        return self.balance_for_bst(
            land_cover=const.WorldCoverClassT(payload.land_cover_class),
            built_up_fraction=payload.built_up_fraction,
            elevation_m=payload.elevation_m,
        )

    @staticmethod
    def _built_up_fraction(land_cover: const.WorldCoverClassT) -> float:
        return 1.0 if land_cover is const.WorldCoverClassT.BUILT_UP else 0.0

    @staticmethod
    def _proximity_score(distance_km: float | None, *, reach_km: float) -> float:
        if distance_km is None:
            return 0.0
        return clamp(1.0 - distance_km / reach_km, minimum=0.0, maximum=1.0)

    @classmethod
    def determine_element_scores(
        cls,
        *,
        land_cover: const.WorldCoverClassT,
        built_up_fraction: float,
        elevation_m: float,
        nearest_marine_km: float | None,
        marine_feature: str | None,
        nearest_inland_water_km: float | None,
        inland_feature: str | None,
        solar_phase: generation_types.SolarPhase,
    ) -> dict[VibemonTypeT, float]:
        score: collections.defaultdict[VibemonTypeT, float] = collections.defaultdict(float)

        for element, weight in land_cover.profile.base_weights.items():
            score[element] += weight

        for element, weight in const.SOLAR_PHASE_BONUS[solar_phase].items():
            score[element] += weight

        urbanity = clamp(built_up_fraction, minimum=0.0, maximum=1.0)

        for element, weight in const.URBAN_ELEMENT_WEIGHTS.items():
            score[element] += urbanity * weight

        for element, weight in const.NATURAL_ELEMENT_WEIGHTS.items():
            score[element] += (1.0 - urbanity) * weight

        elevation_signal = Signal(
            name="elevat",
            attr="elevation_m",
            raw=elevation_m,
            min=-430.0,
            med=350.0,
            max=5100.0,
        ).center

        for element, weight in const.HIGH_ELEVATION_ELEMENT_WEIGHTS.items():
            score[element] += elevation_signal * weight

        water_gate = land_cover.profile.water_proximity_gate
        marine_score = cls._proximity_score(nearest_marine_km, reach_km=const.MARINE_WATER_REACH_KM) * water_gate
        inland_score = cls._proximity_score(nearest_inland_water_km, reach_km=const.INLAND_WATER_REACH_KM) * water_gate

        score[VibemonTypeT.WATER] += max(marine_score, inland_score)

        if marine_feature in {"coastline", "bay", "lake"}:
            score[VibemonTypeT.WATER] += const.MARINE_FEATURE_BONUS * marine_score

        if inland_feature in {"river", "canal", "stream"}:
            score[VibemonTypeT.WATER] += const.INLAND_FEATURE_BONUS * inland_score

        if inland_feature == "lake":
            score[VibemonTypeT.WATER] += const.LAKE_FEATURE_BONUS * inland_score

        if land_cover is const.WorldCoverClassT.BUILT_UP:
            marine_raw = cls._proximity_score(nearest_marine_km, reach_km=const.MARINE_WATER_REACH_KM)
            inland_raw = cls._proximity_score(nearest_inland_water_km, reach_km=const.INLAND_WATER_REACH_KM)
            close_water = max(marine_raw, inland_raw)

            if close_water >= const.BUILT_UP_CLOSE_WATER_THRESHOLD:
                score[VibemonTypeT.WATER] += const.BUILT_UP_CLOSE_WATER_BONUS * close_water

        score[VibemonTypeT.NORMAL] += 0.2 * (1.0 - max(score.values(), default=0.0))

        return dict(score)

    # ── CORE PROTOCOL MEMBERS ─────────────────────────────────────────────────────────

    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> biome_schema.BiomePayload:
        latitude, longitude = seed.geo_coords
        worldcover_task = asyncio.create_task(self.worldcover.sample_class(latitude, longitude))
        elevation_task = asyncio.create_task(self.elevation.point(latitude, longitude))
        water_task = asyncio.create_task(self.water.proximity(latitude, longitude))

        land_cover = await worldcover_task
        elevation_m = await elevation_task
        try:
            water = await water_task
        except Exception:
            _LOGGER.exception("biome_water_fetch_failed", latitude=latitude, longitude=longitude)
            water: dict[str, float | str | None] = {
                "nearest_marine_km": None,
                "marine_feature": None,
                "nearest_inland_water_km": None,
                "inland_feature": None,
            }

        built_up_fraction = self._built_up_fraction(land_cover)
        return biome_schema.BiomePayload(
            land_cover_class=land_cover.value,
            built_up_fraction=built_up_fraction,
            elevation_m=elevation_m,
            solar_phase=seed.solar_phase.value,
            nearest_marine_km=water.get("nearest_marine_km"),  # type: ignore[arg-type]
            marine_feature=water.get("marine_feature"),  # type: ignore[arg-type]
            nearest_inland_water_km=water.get("nearest_inland_water_km"),  # type: ignore[arg-type]
            inland_feature=water.get("inland_feature"),  # type: ignore[arg-type]
        )

    async def synthesize(self, seed: BirthSeed, payload: biome_schema.BiomePayload) -> Affinity:
        rng = seed.rng(f"provider.{self.name}.moves")
        land_cover = const.WorldCoverClassT(payload.land_cover_class)
        built_up_fraction = payload.built_up_fraction
        elevation_m = payload.elevation_m
        solar_phase = generation_types.SolarPhase(payload.solar_phase)

        rankings = self.determine_element_scores(
            land_cover=land_cover,
            built_up_fraction=built_up_fraction,
            elevation_m=elevation_m,
            nearest_marine_km=payload.nearest_marine_km,
            marine_feature=payload.marine_feature,
            nearest_inland_water_km=payload.nearest_inland_water_km,
            inland_feature=payload.inland_feature,
            solar_phase=solar_phase,
        )
        elements = filter_element_types(rankings)
        normalized = self.balance_for_bst(
            land_cover=land_cover,
            built_up_fraction=built_up_fraction,
            elevation_m=elevation_m,
        )
        base_stats = normalized.scaled(elements=elements)

        return Affinity(
            identity=Identity(name="__", elements=elements, base=base_stats),
            visual_notes=land_cover.profile.flavor,
            intensity=const.INTENSITY,
            provider_id=self.name,
            element_rankings=rankings,
            moves=pick_starter_moves(
                moves=self.selectable_moves(),
                rankings=rankings,
                elements=elements,
                k=10,
                rng=rng,
            ),
        )
