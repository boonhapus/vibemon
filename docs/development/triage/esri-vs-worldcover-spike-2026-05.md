# Esri vs WorldCover land-cover spike (May 2026)

Script: `vibemon/backend/scripts/spike_esri_landcover.py`  
Run: `uv run --with pystac-client --with planetary-computer --with rasterio --with pyproj python scripts/spike_esri_landcover.py`

## Question

Is Esri / Impact Observatory (`io-lulc-annual-v02`) worth the extra access complexity for **newer** land cover than ESA WorldCover 2021?

## Latest vintage available (Planetary Computer)

| Product | Newest map year on PC | Access |
|---------|----------------------|--------|
| **Esri io-lulc-annual-v02** | **2023** (`*-2023` STAC items; `start_datetime=2023-01-01`) | STAC + signed COG + **rasterio + pyproj** |
| **ESA WorldCover** | **2021** (`TIME=2021-01-01` on Terrascope WMTS) | WMTS KVP + **Pillow** + RGB legend |

No `*-2024` STAC items found on Planetary Computer during this spike (May 2026). Searching `datetime=2024` returns 2023 items whose interval ends at `2024-01-01`.

**Recency win for Esri today: ~2 years** (2023 vs 2021), not ~5 years.

## Side-by-side at spike coordinates

| Label | WorldCover 2021 | Esri 2021 | Esri 2023 | Esri 21↔WC | Esri 23↔WC | Change 21→23 |
|-------|-----------------|-----------|-----------|------------|------------|--------------|
| amazon_forest | tree_cover | trees | trees | match | match | same |
| london | built_up | built_area | built_area | match | match | same |
| kansas | grassland | crops | **built_area** | match | **DIFF** | **crops → built_area** |
| bergen_coast | built_up | built_area | built_area | match | match | same |
| sahara | bare_sparse | rangeland | rangeland | match | match | same |
| thames_riverside | built_up | built_area | built_area | match | match | same |

Esri class changed **2021→2023 at 1/6** coords (Kansas). That is the kind of signal recency buys — though it may be real development, Esri model drift, or misclassification (verify before tuning).

## Taxonomy differences (not bugs)

Esri uses **9 classes** (Trees, Rangeland, Crops, Built area, …). WorldCover uses **11** (tree_cover, shrubland, grassland, wetland, mangroves, …).

Rough compatibility is good at these coords, but `grassland` ↔ `rangeland`/`crops` and `bare_sparse` ↔ `rangeland` are expected crosswalk fuzz.

## Esri access gotchas (implementation)

1. **COG coordinates are projected (UTM)** — must transform WGS84 with pyproj before `dataset.index()`; lon/lat passed directly returns nodata/0.
2. **Pick STAC item by map year suffix** (`30U-2023`) and geographic bbox, not first search hit.
3. **Cloud class (10)** — use small neighborhood modal filter excluding 0/cloud.
4. **Dependencies:** `pystac-client`, `planetary-computer`, `rasterio`, `pyproj` (not needed for WorldCover WMTS path).
5. **Rate limits:** Planetary Computer signing; optional API key for production volume.

## Recommendation

| Priority | Choice |
|----------|--------|
| **Recency matters** (new build, recent land change) | **Esri 2023** via Planetary Computer — accept STAC/COG stack |
| **Simplicity + stable 11-class FAO taxonomy** | **WorldCover 2021** WMTS + Pillow — already spiked green |
| **Hybrid** | Esri for `land_cover_class` + year; keep Open-Meteo elevation + OSM water unchanged |

Esri does **not** replace GHSL built-up % or OSM water. Built area class is still binary-ish urban signal.

## If choosing Esri

Snapshot payload should include:

```python
{
    "land_cover_source": "esri_io_lulc",
    "land_cover_map_year": 2023,
    "land_cover_class": "built_area",
    "land_cover_value": 7,
    "stac_item_id": "30U-2023",
    # built_up_fraction: 1.0 if built_area else 0.0 until GHSL
}
```

Water fields unchanged: `nearest_marine_km`, `marine_feature`, `nearest_inland_water_km`, `inland_feature`.
