"""Celestial birth provider."""

from typing import ClassVar
import collections

from app.core.math import angular_distance, clamp
from app.domains.generation import types as generation_types
from app.domains.generation.affinity import Affinity
from app.domains.generation.merge import filter_element_types
from app.domains.generation.ports import TrainerSecrets
from app.domains.generation.seed import BirthSeed
from app.domains.move.types import VibemonTypeT
from app.domains.vibemon.identity import Identity
from app.providers import catalog_schema as catalog
from app.providers import schema as providers_schema
from app.providers.base import VibeProvider
from app.providers.celestial import const
from app.providers.celestial import schema as celestial_schema
from app.providers.celestial.ephemeris import models
from app.providers.celestial.ephemeris.engine import compute_chart, sign_name
from app.providers.helpers import pick_starter_moves


class CelestialProvider(VibeProvider[celestial_schema.CelestialPayload]):
    """
    A Vibemon hatches beneath the stories written across the sky.

    One hatched under a full moon over open desert reads differently from one
    under a dawn conjunction above city haze - same hour on the clock, different
    light on the horizon.
    """

    name = "celestial"
    display_label = "STARS"
    tagline = "Moonlight, horizon light, and the chart at birth."

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.ELECTRIC, "sun above the horizon in open daylight"),
        (VibemonTypeT.FLYING, "air-sign Sun, Moon, or rising (secondary)"),
        (VibemonTypeT.GHOST, "deep night, dusk, or planet-bare sky"),
        (VibemonTypeT.DARK, "nautical night and eclipse windows"),
        (VibemonTypeT.PSYCHIC, "dawn light and near-full moon"),
        (VibemonTypeT.FAIRY, "civil dawn and dusk twilight"),
        (VibemonTypeT.FIRE, "midsummer twilight fringe or fire-sign chart"),
        (VibemonTypeT.GRASS, "waxing moon at twilight fringe"),
        (VibemonTypeT.WATER, "waning dusk fringe or water-sign chart"),
        (VibemonTypeT.ICE, "midwinter waning moon at twilight fringe"),
        (VibemonTypeT.ROCK, "earth-sign Sun, Moon, or rising (secondary)"),
    ]

    requirements = (catalog.GEOLOCATION_REQUIREMENT,)
    data_sources = (
        catalog.DataSourceInfo(
            name="Ephemeris computation",
            description="Offline sky chart from birth timestamp and coordinates.",
        ),
    )

    payload_type = celestial_schema.CelestialPayload

    # ── INTERNAL HELPERS ──────────────────────────────────────────────────────────────

    @classmethod
    def _moon_elongation(cls, chart: models.CelestialChart) -> float:
        """Moon-Sun elongation in [0, 360): < 180 is waxing, >= 180 is waning."""
        bodies = chart.bodies_by_name
        return (bodies["moon"].ecliptic_longitude - bodies["sun"].ecliptic_longitude) % 360.0

    @classmethod
    def _moon_is_waxing(cls, chart: models.CelestialChart) -> bool:
        return cls._moon_elongation(chart) < 180.0

    @classmethod
    def _big_three_signs(cls, chart: models.CelestialChart) -> dict[str, str]:
        bodies = chart.bodies_by_name
        return {
            "sun": bodies["sun"].sign,
            "moon": bodies["moon"].sign,
            "ascendant": sign_name(chart.house_cusps[0]),
        }

    @classmethod
    def _has_stellium(cls, chart: models.CelestialChart) -> bool:
        signs = {body.sign for body in chart.bodies if body.name in const.TRADITIONAL_BODIES}
        return len(signs) <= const.STELLIUM_SIGN_COUNT

    @classmethod
    def _chart_dominant_element(
        cls,
        chart: models.CelestialChart,
        chart_rankings: dict[VibemonTypeT, float],
    ) -> VibemonTypeT | None:
        """
        The chart's dominant classical element, if any.

        A chart is element-dominant when at least two of the big three (Sun,
        Moon, Ascendant) share a classical element, or when a stellium
        concentrates the traditional bodies behind the chart's score leader.
        A scattered chart has no dominant element and earns no secondary type.
        """
        big_three = cls._big_three_signs(chart)
        counts = collections.Counter(const.SIGN_ELEMENT[sign] for sign in big_three.values())
        leader, count = counts.most_common(1)[0]
        if count >= 2:
            return leader

        if cls._has_stellium(chart) and chart_rankings:
            return max(chart_rankings, key=chart_rankings.get)

        return None

    @classmethod
    def _sky_rankings(cls, chart: models.CelestialChart) -> dict[VibemonTypeT, float]:
        """Score elements from the observable sky: solar phase, moon, sun arc, eclipse."""
        score: collections.defaultdict[VibemonTypeT, float] = collections.defaultdict(float)
        bodies = chart.bodies_by_name
        sun_altitude = bodies["sun"].altitude_deg
        is_twilight = chart.solar_phase in {generation_types.SolarPhase.DAWN, generation_types.SolarPhase.DUSK}

        # Solar-phase leaders, damped toward the edges of the dawn/dusk band.
        phase_weight = chart.twilight_prevalence if is_twilight else 1.0
        for element, weight in const.SOLAR_PHASE_ELEMENTS[chart.solar_phase]:
            score[element] += weight * phase_weight

        # Moon: full/new bands trump waxing/waning growth; at twilight the moon
        # is damped less the closer the birth sits to the edge of the band.
        moon_weight = 1.0
        if is_twilight:
            moon_weight = max(
                const.TWILIGHT_MOON_DAMPING_FLOOR,
                1.0 - const.TWILIGHT_MOON_PHASE_DAMPING * phase_weight,
            )

        if chart.moon_illumination > const.FULL_MOON_MIN_ILLUMINATION:
            moon_elements = const.FULL_MOON_ELEMENTS
        elif chart.moon_illumination < const.NEW_MOON_MAX_ILLUMINATION:
            moon_elements = const.NEW_MOON_ELEMENTS
        elif cls._moon_is_waxing(chart):
            moon_elements = const.MOON_GROWTH_ELEMENTS
        else:
            moon_elements = const.MOON_RECESSION_ELEMENTS

        for element, weight in moon_elements:
            score[element] += weight * moon_weight

        # Sun altitude: deep night below nautical twilight, open daylight above.
        if sun_altitude < const.DEEP_NIGHT_SUN_ALTITUDE_DEG:
            for element, weight in const.DEEP_NIGHT_ELEMENTS:
                score[element] += weight
        elif sun_altitude > 0.0 and chart.solar_phase is generation_types.SolarPhase.DAY:
            for element, weight in const.DAYTIME_SUN_ELEMENTS:
                score[element] += weight

        # Season from the Sun's position along the ecliptic.
        for element, weight in cls._seasonal_elements(bodies["sun"].ecliptic_longitude):
            score[element] += weight

        # Bare deep-night sky: no naked-eye planet above the horizon.
        any_planet_visible = any(bodies[name].visible for name in const.VISIBLE_PLANETS)
        if not any_planet_visible and sun_altitude < const.DEEP_NIGHT_SUN_ALTITUDE_DEG:
            score[VibemonTypeT.GHOST] += const.BARE_SKY_GHOST_BOOST

        if chart.eclipse_season:
            for element, weight in const.ECLIPSE_ELEMENT_BOOST:
                score[element] += weight

        return dict(score)

    @classmethod
    def _chart_element_rankings(cls, chart: models.CelestialChart) -> dict[VibemonTypeT, float]:
        """Score classical elements from the big three signs, boosted by a stellium."""
        score: collections.defaultdict[VibemonTypeT, float] = collections.defaultdict(float)
        bodies = chart.bodies_by_name
        ascendant_sign = sign_name(chart.house_cusps[0])

        for point, weight in const.CHART_POINT_WEIGHTS.items():
            sign = ascendant_sign if point == "ascendant" else bodies[point].sign
            score[const.SIGN_ELEMENT[sign]] += weight

        if cls._has_stellium(chart) and score:
            dominant = max(score, key=score.get)
            score[dominant] *= const.STELLIUM_ELEMENT_BOOST

        return dict(score)

    @classmethod
    def _pick_celestial_elements(
        cls,
        *,
        sky_rankings: dict[VibemonTypeT, float],
        chart_rankings: dict[VibemonTypeT, float],
        chart_dominant: VibemonTypeT | None,
    ) -> tuple[tuple[VibemonTypeT, ...], dict[VibemonTypeT, float]]:
        """
        Sky owns slot 1; the chart's dominant element, when one exists, owns slot 2.

        A scattered chart (no dominant element) yields a single-typed Vibemon.
        When the chart's dominant element already won the sky primary, the chart
        reinforces slot 1 instead of granting a separate secondary.
        """
        primary_candidates = filter_element_types(sky_rankings)
        primary = primary_candidates[0]

        secondary = chart_dominant if chart_dominant is not None and chart_dominant != primary else None

        elements = (primary, secondary) if secondary is not None else (primary,)
        combined = dict(sky_rankings)
        for element, weight in chart_rankings.items():
            combined[element] = combined.get(element, 0.0) + weight
        return elements, combined

    @classmethod
    def _season_arc(cls, sun_longitude: float) -> const.SeasonArcT | None:
        """Which solstice arc the Sun sits in, if any (Cancer 90°, Capricorn 270°)."""
        if angular_distance(sun_longitude, 270.0) <= const.SEASONAL_SUN_ARC_DEGREES:
            return "midwinter"
        if angular_distance(sun_longitude, 90.0) <= const.SEASONAL_SUN_ARC_DEGREES:
            return "midsummer"
        return None

    @classmethod
    def _seasonal_elements(cls, sun_longitude: float) -> tuple[tuple[VibemonTypeT, float], ...]:
        match cls._season_arc(sun_longitude):
            case "midwinter":
                return const.SEASONAL_MIDWINTER_ELEMENTS
            case "midsummer":
                return const.SEASONAL_MIDSUMMER_ELEMENTS
            case None:
                return ()

    @classmethod
    def _dignity_score(cls, body: str, sign: str) -> float:
        score = 0.55
        if sign in const.DOMICILE.get(body, frozenset()):
            score = 1.0
        elif const.EXALTATION.get(body) == sign:
            score = 0.85
        return score

    @classmethod
    def _astronomy_body_factor(cls, body: models.BodyObservation) -> float:
        altitude_factor = clamp((body.altitude_deg + 12.0) / 60.0, minimum=0.0, maximum=1.0)
        return 0.35 + 0.65 * altitude_factor if body.visible else 0.25

    @classmethod
    def _astrology_body_factor(cls, body: models.BodyObservation) -> float:
        return 0.35 + 0.65 * const.HOUSE_WEIGHT[body.house] * cls._dignity_score(body.name, body.sign)

    # ── CORE PROTOCOL MEMBERS ─────────────────────────────────────────────────────────

    async def fetch(
        self,
        seed: BirthSeed,
        *,
        secrets: TrainerSecrets | None = None,
    ) -> celestial_schema.CelestialPayload:
        latitude, longitude = seed.geo_coords
        chart = compute_chart(
            timestamp=seed.timestamp,
            latitude=latitude,
            longitude=longitude,
            timezone=seed.local_timezone,
        )
        return celestial_schema.CelestialPayload(chart=chart)

    async def synthesize(self, seed: BirthSeed, payload: celestial_schema.CelestialPayload) -> Affinity:
        """Translate a captured sky chart to Affinity components."""
        rng = seed.rng(f"provider.{self.name}.moves")
        chart = payload.chart

        # RANKED ELEMENTS BASED ON THE DATA
        sky_rankings = self._sky_rankings(chart)
        chart_rankings = self._chart_element_rankings(chart)
        elements, rankings = self._pick_celestial_elements(
            sky_rankings=sky_rankings,
            chart_rankings=chart_rankings,
            chart_dominant=self._chart_dominant_element(chart, chart_rankings),
        )

        # BALANCE SIGNAL DATA FOR BASE STAT TRANSLATION
        base_stats = self.balance_for_bst(chart).scaled(elements=elements)

        return Affinity(
            identity=Identity(name="__", elements=elements, base=base_stats),
            visual_notes=self.visual_notes(chart),
            intensity=self.calculate_intensity(chart),
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

    # ── PROTOCOL HELPERS ──────────────────────────────────────────────────────────────

    @classmethod
    def balance_for_bst(cls, chart: models.CelestialChart) -> providers_schema.BaseStatCenters:
        """Blend each planet's astronomy (altitude) and astrology (house, dignity) factors."""
        bodies = chart.bodies_by_name
        below_horizon = sum(1 for body in chart.bodies if not body.visible and body.name in const.TRADITIONAL_BODIES)
        hp = clamp(below_horizon / len(const.TRADITIONAL_BODIES), minimum=0.0, maximum=1.0)

        def blended(body_name: str) -> float:
            body = bodies[body_name]
            return clamp(
                cls._astronomy_body_factor(body) * cls._astrology_body_factor(body),
                minimum=0.0,
                maximum=1.0,
            )

        return providers_schema.BaseStatCenters(
            hp=hp,
            attack=blended("mars"),
            defense=blended("saturn"),
            sp_attack=blended("sun"),
            sp_defense=blended("moon"),
            speed=blended("mercury"),
        )

    @classmethod
    def calculate_intensity(cls, chart: models.CelestialChart) -> float:
        """Angular bodies set the base; lunation extremes, eclipses, and tight aspects add."""
        bodies = chart.bodies_by_name
        angular = sum(1 for name in const.TRADITIONAL_BODIES if bodies[name].house in const.ANGULAR_HOUSES)
        base = angular / len(const.TRADITIONAL_BODIES)

        lunation = max(abs(chart.moon_illumination - 0.5) * 2.0, 0.0) * 0.15
        eclipse = 0.12 if chart.eclipse_season else 0.0
        tight_aspects = sum(1 for aspect in chart.aspects if aspect.orb_deg <= const.TIGHT_ASPECT_MAX_ORB)
        tension = min(tight_aspects, 4) / 4.0 * 0.10
        return round(clamp(base + lunation + eclipse + tension, minimum=0.0, maximum=1.0), ndigits=4)

    @classmethod
    def _moon_bucket(cls, chart: models.CelestialChart) -> const.MoonBucketT:
        if chart.moon_illumination > const.FULL_MOON_MIN_ILLUMINATION:
            return "full"
        if chart.moon_illumination < const.NEW_MOON_MAX_ILLUMINATION:
            return "new"

        elongation = cls._moon_elongation(chart)
        if elongation < 90.0:
            return "waxing_crescent"
        if elongation < 180.0:
            return "waxing_gibbous"
        if elongation < 270.0:
            return "waning_gibbous"
        return "waning_crescent"

    @classmethod
    def visual_notes(cls, chart: models.CelestialChart) -> str:
        """Compose creature-facing cues: moon marking base, horizon light, then gated accents."""
        parts = [
            const.MOON_VISUALS[cls._moon_bucket(chart)],
            const.SOLAR_PHASE_VISUALS[chart.solar_phase],
        ]

        if season := cls._season_arc(chart.bodies_by_name["sun"].ecliptic_longitude):
            parts.append(const.SEASON_VISUALS[season])

        if chart.eclipse_season:
            parts.append(const.ECLIPSE_VISUAL)

        return "; ".join(parts)
