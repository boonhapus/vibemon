from io import BytesIO
import collections
import datetime as dt
import pathlib

from PIL import Image
import pytest

from app.domains.generation.merge import filter_element_types
from app.domains.generation.seed import BirthSeed
from app.domains.move import universal
from app.domains.move.types import VibemonTypeT
from app.providers.biome import schema as biome_schema
from app.providers.biome.const import WorldCoverClassT
from app.providers.biome.provider import BiomeProvider
from app.providers.biome.raster.worldcover import api as worldcover_api
from tests.conftest import TEST_TRAINER_ID


def test_biome_move_catalog_has_fifteen_moves_per_exposed_element() -> None:
    provider = BiomeProvider()
    exposed_types = set(provider.get_exposed_elements())

    catalog_types = {move.type for move in provider.moves()}
    move_counts = collections.Counter(move.type for move in provider.moves())

    assert catalog_types <= exposed_types
    assert move_counts == {element: 15 for element in exposed_types}


def test_biome_selectable_moves_include_shared_universal_moves_once() -> None:
    provider = BiomeProvider()

    universal_ids = {move.id for move in universal.moves()}
    selectable_ids = [move.id for move in provider.selectable_moves(level=99)]

    assert universal_ids <= set(selectable_ids)
    assert len(selectable_ids) == len(set(selectable_ids))
    assert len(selectable_ids) == len(provider.moves()) + len(universal.moves())


def test_worldcover_decode_known_rgb_values() -> None:
    assert worldcover_api.TerrascopeWorldCoverClient.decode_rgb((0, 100, 0)) is WorldCoverClassT.TREE_COVER
    assert worldcover_api.TerrascopeWorldCoverClient.decode_rgb((250, 0, 0)) is WorldCoverClassT.BUILT_UP
    assert worldcover_api.TerrascopeWorldCoverClient.decode_rgb((180, 180, 180)) is WorldCoverClassT.BARE_SPARSE


def test_worldcover_fixture_png_decodes_to_tree_cover() -> None:
    fixture_path = (
        pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "biome" / "worldcover_amazon_z13_tx2680_ty4174.png"
    )
    image = Image.open(BytesIO(fixture_path.read_bytes())).convert("RGBA")
    pixel = image.getpixel((128, 128))
    assert isinstance(pixel, tuple)
    red, green, blue, _alpha = pixel
    assert worldcover_api.TerrascopeWorldCoverClient.decode_rgb((red, green, blue)) is WorldCoverClassT.TREE_COVER


def test_worldcover_nodata_tile_returns_permanent_water() -> None:
    image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    result = worldcover_api.TerrascopeWorldCoverClient.classify_tile_at_point(
        image,
        latitude=-13.133140200776296,
        longitude=173.1623252194193,
        tile_x=8036,
        tile_y=4397,
        zoom=13,
    )
    assert result is WorldCoverClassT.PERMANENT_WATER


def test_determine_element_scores_boosts_built_up_elements() -> None:
    scores = BiomeProvider.determine_element_scores(
        land_cover=WorldCoverClassT.BUILT_UP,
        built_up_fraction=1.0,
        elevation_m=16.0,
        nearest_marine_km=22.0,
        marine_feature="bay",
        nearest_inland_water_km=0.2,
        inland_feature="river",
    )
    assert scores[VibemonTypeT.STEEL] > scores[VibemonTypeT.ICE]
    assert scores[VibemonTypeT.WATER] > 0.0
    assert scores[VibemonTypeT.STEEL] > scores[VibemonTypeT.WATER]


def test_river_near_forest_does_not_beat_grass_identity() -> None:
    scores = BiomeProvider.determine_element_scores(
        land_cover=WorldCoverClassT.TREE_COVER,
        built_up_fraction=0.0,
        elevation_m=50.0,
        nearest_marine_km=None,
        marine_feature=None,
        nearest_inland_water_km=2.3,
        inland_feature="river",
    )
    elements = filter_element_types(scores)
    assert elements[0] is VibemonTypeT.GRASS
    assert VibemonTypeT.WATER not in elements


def test_grassland_pond_does_not_beat_grass_identity() -> None:
    scores = BiomeProvider.determine_element_scores(
        land_cover=WorldCoverClassT.GRASSLAND,
        built_up_fraction=0.0,
        elevation_m=576.0,
        nearest_marine_km=None,
        marine_feature=None,
        nearest_inland_water_km=0.48,
        inland_feature="water",
    )
    elements = filter_element_types(scores)
    assert elements[0] is VibemonTypeT.GRASS
    assert VibemonTypeT.WATER not in elements


def test_canal_city_gets_steel_water_dual_typing() -> None:
    scores = BiomeProvider.determine_element_scores(
        land_cover=WorldCoverClassT.BUILT_UP,
        built_up_fraction=1.0,
        elevation_m=4.0,
        nearest_marine_km=8.24,
        marine_feature="coastline",
        nearest_inland_water_km=0.14,
        inland_feature="canal",
    )
    assert filter_element_types(scores) == (VibemonTypeT.STEEL, VibemonTypeT.WATER)


def test_inland_suburban_city_stays_steel_electric() -> None:
    scores = BiomeProvider.determine_element_scores(
        land_cover=WorldCoverClassT.BUILT_UP,
        built_up_fraction=1.0,
        elevation_m=206.0,
        nearest_marine_km=None,
        marine_feature=None,
        nearest_inland_water_km=5.0,
        inland_feature="water",
    )
    assert filter_element_types(scores) == (VibemonTypeT.STEEL, VibemonTypeT.ELECTRIC)


def test_intensity_constant_is_half() -> None:
    from app.providers.biome import const

    assert const.INTENSITY == 0.5


def test_visual_notes_built_up_near_inland_water() -> None:
    payload = biome_schema.BiomePayload(
        land_cover_class="built_up",
        built_up_fraction=1.0,
        elevation_m=16.0,
        nearest_marine_km=22.25,
        marine_feature="bay",
        nearest_inland_water_km=0.08,
        inland_feature="water",
    )

    notes = BiomeProvider.visual_notes(payload)

    assert notes.startswith("concrete-grey plating, soot-dark joint lines")
    assert "still-water mirror flecks" in notes


def test_visual_notes_high_elevation_adds_ridge_cue() -> None:
    payload = biome_schema.BiomePayload(
        land_cover_class="bare_sparse",
        built_up_fraction=0.0,
        elevation_m=2800.0,
        nearest_marine_km=None,
        marine_feature=None,
        nearest_inland_water_km=None,
        inland_feature=None,
    )

    notes = BiomeProvider.visual_notes(payload)

    assert notes.startswith("cracked clay hide, pale dust-veiled joints")
    assert "wind-scored ridge edges" in notes


def test_visual_notes_coastal_canal_city_prefers_near_inland_water() -> None:
    payload = biome_schema.BiomePayload(
        land_cover_class="built_up",
        built_up_fraction=1.0,
        elevation_m=4.0,
        nearest_marine_km=8.24,
        marine_feature="coastline",
        nearest_inland_water_km=0.14,
        inland_feature="canal",
    )

    notes = BiomeProvider.visual_notes(payload)

    assert "concrete-grey plating" in notes
    assert "canal-stain streaks" in notes
    assert "salt-spray patina" not in notes


def test_visual_notes_coastal_without_near_inland_water() -> None:
    payload = biome_schema.BiomePayload(
        land_cover_class="built_up",
        built_up_fraction=1.0,
        elevation_m=4.0,
        nearest_marine_km=3.0,
        marine_feature="coastline",
        nearest_inland_water_km=12.0,
        inland_feature="water",
    )

    notes = BiomeProvider.visual_notes(payload)

    assert "concrete-grey plating" in notes
    assert "salt-spray patina" in notes


def test_visual_notes_water_native_land_cover_skips_proximity_layer() -> None:
    payload = biome_schema.BiomePayload(
        land_cover_class="permanent_water",
        built_up_fraction=0.0,
        elevation_m=0.0,
        nearest_marine_km=0.5,
        marine_feature="coastline",
        nearest_inland_water_km=0.1,
        inland_feature="river",
    )

    notes = BiomeProvider.visual_notes(payload)

    assert notes == "sleek wet gloss, ripple-light belly markings; lowland-soft belly, river-plain dampness"


@pytest.mark.asyncio
async def test_synthesize_replay_from_london_payload() -> None:
    provider = BiomeProvider()
    seed = BirthSeed(
        timestamp=dt.datetime(2026, 5, 19, 12, 0, tzinfo=dt.UTC),
        geo_coords=(51.5074, -0.1278),
        trainer_id=TEST_TRAINER_ID,
        providers=[provider],
    )
    payload = {
        "land_cover_class": "built_up",
        "built_up_fraction": 1.0,
        "elevation_m": 16.0,
        "nearest_marine_km": 22.25,
        "marine_feature": "bay",
        "nearest_inland_water_km": 0.08,
        "inland_feature": "water",
    }

    first = await provider.synthesize(seed, BiomeProvider.parse_payload(payload))
    second = await provider.synthesize(seed, BiomeProvider.parse_payload(payload))

    assert first.provider_id == "biome"
    assert first.intensity == 0.5
    assert first.visual_notes == ("concrete-grey plating, soot-dark joint lines; still-water mirror flecks")
    assert first.identity.model_dump(exclude={"generated_at"}) == second.identity.model_dump(exclude={"generated_at"})
    assert [move.id for move in first.moves] == [move.id for move in second.moves]
