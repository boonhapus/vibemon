"""BiomeProvider: place-of-birth affinity from land cover, elevation, water, and solar phase."""

from typing import Any, ClassVar
import asyncio
import collections
import functools as ft

import structlog

from app.core.math import clamp
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import Identity
from app.domains.vibemon.strength_formulas import base_stat_asymmetric_scaling, stat_ratio_from_grade
from app.providers.base import VibeProvider
from app.providers.helpers import Signal, filter_element_types, pick_starter_moves

from . import const
from .raster.elevation import api as elevation_api
from .raster.worldcover import api as worldcover_api
from .water.overpass import api as overpass_api

_LOGGER = structlog.get_logger(__name__)


class BiomeProvider(VibeProvider):
    """
    A Vibemon is born from the ground beneath its birthplace.

    ESA WorldCover land cover, Open-Meteo elevation, and OSM water proximity fold
    into an `Affinity` for the physical place.

    Six stats start from land-cover archetype tiers: urbanity raises Speed and
    Sp. Attack while lowering HP and Sp. Defense, elevation raises Defense and
    lowers Speed, and Attack follows the class baseline.

    A creature born in London streets reads differently from one in Amazon tree
    cover or Sahara bare ground — elements and stats both emerge from where it
    was born.
    """

    name = "biome"

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

    def __init__(self) -> None:
        self.worldcover = worldcover_api.TerrascopeWorldCoverClient()
        self.elevation = elevation_api.OpenMeteoElevationClient()
        self.water = overpass_api.OverpassWaterClient()

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

    @classmethod
    def _stat_centers(
        cls,
        *,
        land_cover: const.WorldCoverClassT,
        built_up_fraction: float,
        elevation_m: float,
    ) -> dict[str, float]:
        archetype = land_cover.profile.stat_archetype
        centers = {stat: const.STAT_TIER_CENTER[tier] for stat, tier in archetype.items()}

        urbanity = clamp(built_up_fraction, minimum=0.0, maximum=1.0)
        elevation_signal = Signal(
            name="elevat",
            attr="elevation_m",
            raw=elevation_m,
            min=-430.0,
            med=350.0,
            max=5100.0,
        ).center

        centers["speed"] = clamp(centers["speed"] + 0.08 * urbanity - 0.08 * elevation_signal, minimum=0.0, maximum=1.0)
        centers["sp_attack"] = clamp(centers["sp_attack"] + 0.08 * urbanity, minimum=0.0, maximum=1.0)
        centers["hp"] = clamp(centers["hp"] - 0.08 * urbanity, minimum=0.0, maximum=1.0)
        centers["sp_defense"] = clamp(centers["sp_defense"] - 0.08 * urbanity, minimum=0.0, maximum=1.0)
        centers["defense"] = clamp(centers["defense"] + 0.08 * elevation_signal, minimum=0.0, maximum=1.0)
        return centers

    async def fetch(self, seed: BirthSeed) -> dict[str, Any]:
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
        return {
            "land_cover_class": land_cover.value,
            "built_up_fraction": built_up_fraction,
            "elevation_m": elevation_m,
            "solar_phase": seed.solar_phase.value,
            **water,
        }

    async def synthesize(self, seed: BirthSeed, payload: dict[str, Any]) -> Affinity:
        rng = seed.rng(f"provider.{self.name}.moves")
        land_cover = const.WorldCoverClassT(payload["land_cover_class"])
        built_up_fraction = float(payload["built_up_fraction"])
        elevation_m = float(payload["elevation_m"])
        solar_phase = generation_types.SolarPhase(payload["solar_phase"])

        rankings = self.determine_element_scores(
            land_cover=land_cover,
            built_up_fraction=built_up_fraction,
            elevation_m=elevation_m,
            nearest_marine_km=payload.get("nearest_marine_km"),
            marine_feature=payload.get("marine_feature"),
            nearest_inland_water_km=payload.get("nearest_inland_water_km"),
            inland_feature=payload.get("inland_feature"),
            solar_phase=solar_phase,
        )
        local_elements = filter_element_types(rankings)
        stats = self._stat_centers(
            land_cover=land_cover,
            built_up_fraction=built_up_fraction,
            elevation_m=elevation_m,
        )
        ratio = ft.partial(stat_ratio_from_grade, elements=local_elements)

        # fmt: off
        # ruff: noqa: E501
        affinity = Affinity(
            identity=Identity(
                name="__",
                elements=local_elements,
                base_hp=base_stat_asymmetric_scaling(ratio(stats["hp"], stat="hp"), stat="hp"),
                base_attack=base_stat_asymmetric_scaling(ratio(stats["attack"], stat="attack"), stat="attack"),
                base_defense=base_stat_asymmetric_scaling(ratio(stats["defense"], stat="defense"), stat="defense"),
                base_sp_attack=base_stat_asymmetric_scaling(ratio(stats["sp_attack"], stat="sp_attack"), stat="sp_attack"),
                base_sp_defense=base_stat_asymmetric_scaling(ratio(stats["sp_defense"], stat="sp_defense"), stat="sp_defense"),
                base_speed=base_stat_asymmetric_scaling(ratio(stats["speed"], stat="speed"), stat="speed"),
            ),
            visual_notes=land_cover.profile.flavor,
            intensity=const.INTENSITY,
            provider_id=self.name,
            element_rankings=rankings,
            moves=pick_starter_moves(
                moves=self.selectable_moves(),
                rankings=rankings,
                elements=local_elements,
                k=10,
                rng=rng,
            ),
        )
        # fmt: on

        return affinity
