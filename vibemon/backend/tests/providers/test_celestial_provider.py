import collections
import datetime as dt

import pytest

from app.domains.generation.seed import BirthSeed
from app.domains.move import universal
from app.domains.move.types import VibemonTypeT
from app.providers.celestial.ephemeris import models
from app.providers.celestial.ephemeris.engine import compute_chart
from app.providers.celestial.houses import house_for_longitude, placidus_cusps
from app.providers.celestial.provider import CelestialProvider
from tests.conftest import TEST_TRAINER_ID

_DEFAULT_BODY_SIGNS: dict[str, str] = {
    "sun": "aries",
    "moon": "cancer",
    "mercury": "gemini",
    "venus": "taurus",
    "mars": "leo",
    "jupiter": "sagittarius",
    "saturn": "capricorn",
}


def make_chart(
    *,
    sun_longitude: float = 10.0,
    moon_longitude: float = 100.0,
    body_signs: dict[str, str] | None = None,
    ascendant_longitude: float = 185.0,  # libra rising
    solar_phase: str = "day",
    twilight_prevalence: float = 1.0,
    moon_illumination: float = 0.5,
    eclipse_season: bool = False,
) -> models.CelestialChart:
    signs = _DEFAULT_BODY_SIGNS | (body_signs or {})
    bodies = tuple(
        models.BodyObservation(
            name=name,
            ecliptic_longitude=(
                sun_longitude if name == "sun" else moon_longitude if name == "moon" else 50.0 + index * 30.0
            ),
            altitude_deg=10.0,
            visible=True,
            house=1 + index,
            sign=signs[name],
        )
        for index, name in enumerate(_DEFAULT_BODY_SIGNS)
    )
    return models.CelestialChart(
        timestamp_iso="2024-03-20T12:00:00+00:00",
        latitude=0.0,
        longitude=0.0,
        timezone="UTC",
        solar_phase=solar_phase,
        twilight_prevalence=twilight_prevalence,
        moon_illumination=moon_illumination,
        eclipse_season=eclipse_season,
        house_cusps=tuple((ascendant_longitude + 30.0 * index) % 360.0 for index in range(12)),
        bodies=bodies,
        aspects=(),
    )


def chart_dominant(chart: models.CelestialChart) -> VibemonTypeT | None:
    return CelestialProvider._chart_dominant_element(chart, CelestialProvider._chart_element_rankings(chart))


def test_placidus_cusps_are_twelve_longitudes() -> None:
    jd = 2448027.1041666665
    cusps = placidus_cusps(jd=jd, latitude_deg=51.5, longitude_deg=-0.1)
    assert len(cusps) == 12
    assert all(0.0 <= cusp < 360.0 for cusp in cusps)


def test_house_for_longitude_wraps_across_asc() -> None:
    cusps = (350.0, 20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 320.0)
    assert house_for_longitude(355.0, cusps) == 1
    assert house_for_longitude(10.0, cusps) == 1
    assert house_for_longitude(25.0, cusps) == 2


def test_celestial_move_catalog_has_fifteen_moves_per_exposed_element() -> None:
    provider = CelestialProvider()
    exposed_types = set(provider.get_exposed_elements())
    catalog_types = {move.type for move in provider.moves()}
    move_counts = collections.Counter(move.type for move in provider.moves())

    assert catalog_types <= exposed_types
    assert move_counts == {element: 15 for element in exposed_types}


def test_celestial_selectable_moves_include_shared_universal_moves_once() -> None:
    provider = CelestialProvider()

    universal_ids = {move.id for move in universal.moves()}
    selectable_ids = [move.id for move in provider.selectable_moves(level=99)]

    assert universal_ids <= set(selectable_ids)
    assert len(selectable_ids) == len(set(selectable_ids))
    assert len(selectable_ids) == len(provider.moves()) + len(universal.moves())


@pytest.mark.asyncio
async def test_fetch_and_synthesize_are_deterministic() -> None:
    provider = CelestialProvider()
    seed = BirthSeed(
        timestamp=dt.datetime(2024, 3, 20, 4, 15, tzinfo=dt.UTC),
        geo_coords=(35.6762, 139.6503),
        trainer_id=TEST_TRAINER_ID,
        local_timezone=dt.timezone(dt.timedelta(hours=9)),
        providers=[provider],
    )

    payload = await provider.fetch(seed)
    first = await provider.synthesize(seed, payload)
    second = await provider.synthesize(seed, payload)

    assert payload.chart.solar_phase in {"dawn", "day", "dusk", "night"}
    assert first.provider_id == "celestial"
    assert first.visual_notes
    assert first.identity.model_dump(exclude={"generated_at"}) == second.identity.model_dump(exclude={"generated_at"})
    assert [move.id for move in first.moves] == [move.id for move in second.moves]


def test_moon_waxing_across_zero_wrap() -> None:
    # Sun in late Pisces, Moon just past 0° Aries: 30° elongation, waxing.
    waxing = make_chart(sun_longitude=350.0, moon_longitude=20.0)
    assert CelestialProvider._moon_is_waxing(waxing) is True

    waning = make_chart(sun_longitude=20.0, moon_longitude=350.0)
    assert CelestialProvider._moon_is_waxing(waning) is False


def test_visual_notes_name_lunar_phase_from_elongation() -> None:
    chart = make_chart(sun_longitude=350.0, moon_longitude=20.0)
    assert "waxing-crescent" in CelestialProvider.visual_notes(chart)

    chart = make_chart(sun_longitude=20.0, moon_longitude=350.0)
    assert "waning-crescent" in CelestialProvider.visual_notes(chart)


def test_visual_notes_describe_appearance_cues() -> None:
    # Day-phase chart with a near-full moon: silver moon marking plus daylight cue.
    chart = make_chart(sun_longitude=10.0, moon_longitude=185.0, moon_illumination=0.95)
    notes = CelestialProvider.visual_notes(chart)

    assert "full-moon disc marking" in notes
    assert "daylight" in notes


def test_visual_notes_add_seasonal_and_eclipse_accents() -> None:
    # Sun at 275° sits inside the midwinter (Capricorn) arc.
    chart = make_chart(sun_longitude=275.0, moon_longitude=200.0)
    assert "frost-rimmed edges" in CelestialProvider.visual_notes(chart)

    eclipse_chart = make_chart(eclipse_season=True)
    assert "eclipse ring marking" in CelestialProvider.visual_notes(eclipse_chart)


def test_chart_dominant_element_requires_big_three_agreement() -> None:
    scattered = make_chart()  # fire Sun, water Moon, air Ascendant
    assert chart_dominant(scattered) is None

    agreeing = make_chart(body_signs={"sun": "leo", "moon": "aries"})
    assert chart_dominant(agreeing) is VibemonTypeT.FIRE


def test_chart_dominant_element_ascendant_agreement_counts() -> None:
    # Moon in Libra (air) agrees with the Libra Ascendant against a fire Sun.
    chart = make_chart(body_signs={"moon": "libra"})
    assert chart_dominant(chart) is VibemonTypeT.FLYING


def test_chart_dominant_element_stellium_backs_score_leader() -> None:
    # Big three scattered, but five bodies pile into two signs → stellium.
    chart = make_chart(
        body_signs={
            "mercury": "aries",
            "venus": "aries",
            "mars": "aries",
            "jupiter": "cancer",
            "saturn": "cancer",
        }
    )
    assert chart_dominant(chart) is VibemonTypeT.FIRE


def test_twilight_midpoint_keeps_phase_leader_primary() -> None:
    # Waxing mid-moon at the dawn band midpoint: fairy still owns slot 1.
    chart = make_chart(
        sun_longitude=25.0,
        moon_longitude=100.0,
        solar_phase="dawn",
        twilight_prevalence=1.0,
    )
    rankings = CelestialProvider._sky_rankings(chart)
    assert max(rankings, key=rankings.get) is VibemonTypeT.FAIRY


def test_twilight_edge_waxing_dawn_yields_grass_primary() -> None:
    # Off-season waxing mid-moon at the edge of the dawn band: growth owns the sky.
    chart = make_chart(
        sun_longitude=25.0,
        moon_longitude=100.0,
        solar_phase="dawn",
        twilight_prevalence=0.3,
    )
    rankings = CelestialProvider._sky_rankings(chart)
    assert max(rankings, key=rankings.get) is VibemonTypeT.GRASS
    assert rankings[VibemonTypeT.GRASS] > rankings[VibemonTypeT.FIRE]


def test_twilight_edge_midwinter_waning_dusk_yields_ice_primary() -> None:
    chart = make_chart(
        sun_longitude=285.0,
        moon_longitude=200.0,
        solar_phase="dusk",
        twilight_prevalence=0.3,
    )
    rankings = CelestialProvider._sky_rankings(chart)
    assert max(rankings, key=rankings.get) is VibemonTypeT.ICE
    assert rankings[VibemonTypeT.ICE] > rankings[VibemonTypeT.WATER]


def test_midsummer_heat_outranks_waxing_growth() -> None:
    chart = make_chart(
        sun_longitude=95.0,
        moon_longitude=170.0,
        solar_phase="dawn",
        twilight_prevalence=0.3,
    )
    rankings = CelestialProvider._sky_rankings(chart)
    assert rankings[VibemonTypeT.FIRE] > rankings[VibemonTypeT.GRASS]


def test_offseason_waning_recession_outranks_ice() -> None:
    chart = make_chart(
        sun_longitude=25.0,
        moon_longitude=300.0,
        solar_phase="dusk",
        twilight_prevalence=0.3,
    )
    rankings = CelestialProvider._sky_rankings(chart)
    assert max(rankings, key=rankings.get) is VibemonTypeT.WATER
    assert rankings[VibemonTypeT.WATER] > rankings[VibemonTypeT.ICE]


def test_compute_chart_populates_traditional_bodies() -> None:
    chart = compute_chart(
        timestamp=dt.datetime(2024, 6, 21, 12, 0, tzinfo=dt.UTC),
        latitude=51.5,
        longitude=-0.1,
        timezone=dt.UTC,
    )
    names = {body.name for body in chart.bodies}
    assert names == {"sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn"}
