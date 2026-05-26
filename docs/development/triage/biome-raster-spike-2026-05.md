# Biome raster + water spike (May 2026)

Research script: `vibemon/backend/scripts/spike_biome_raster.py`  
Fixture: `vibemon/backend/tests/fixtures/biome/worldcover_amazon_z13_tx2680_ty4174.png`

## Go / no-go

| Leg | Verdict |
|-----|---------|
| WorldCover via Terrascope WMTS KVP + Pillow | **Go** — 6/6 test coords exact legend match (`legend_dist=0`) |
| GHSL built-up % on Terrascope | **No layer** — use WorldCover `built_up` binary fallback until COG/GHSL path |
| Open-Meteo elevation | **Go** — plausible values |
| OSM Overpass water + features | **Go with caveats** — see below |

---

## Terrascope WMTS v2 (WorldCover)

- **Capabilities:** `https://wmts.terrascope.be/?service=WMTS&request=GetCapabilities`
- **GetTile KVP base:** `https://wmts.terrascope.be/wmts?` (REST-only URLs return 400 without `SERVICE=WMTS`)
- **Layer:** `esa-worldcover-map-10m-2021-v2_map`
- **TIME:** must be `2021-01-01` (date only). `2021-01-01T00:00:00.000Z` is rejected.
- **TileMatrixSet:** `EPSG:3857`
- **Zoom used in spike:** `13` (256×256 PNG tiles)
- **Decode:** center-pixel RGB → ESA legend table (tolerance 0 worked on all samples)

### Sample results

| Label | lat, lon | Class | RGB | Elevation | Expect |
|-------|----------|-------|-----|-----------|--------|
| amazon_forest | -3.47, -62.22 | tree_cover | (0,100,0) | 50 m | OK |
| london | 51.51, -0.13 | built_up | (250,0,0) | 16 m | OK |
| kansas | 39.83, -98.58 | grassland | (255,255,76) | 576 m | OK |
| bergen_coast | 60.39, 5.32 | built_up | (250,0,0) | 14 m | OK (urban fjord; not water pixel) |
| sahara | 23.42, 25.66 | bare_sparse | (180,180,180) | 962 m | OK |
| thames_riverside | 51.51, -0.11 | built_up | (250,0,0) | 7 m | OK |

### GetFeatureInfo (optional)

- Works with `INFOFORMAT=application/geo+json`
- Returns `properties.values` as RGB tuple (e.g. `[250,0,0]`), not raw class code `50`
- **Does not remove Pillow/legend path** unless you treat `values` like a pixel read

### GHSL

No `ghsl` / built-up layers in Terrascope WMTS capabilities (114 layers searched).  
**v1 built_up_fraction:** `1.0` if `land_cover_class == built_up` else `0.0`.

---

## Open-Meteo elevation

- `GET https://api.open-meteo.com/v1/elevation?latitude=&longitude=`
- Same sanity as spike table above.

---

## OSM Overpass (water + features)

- **Endpoints:** `overpass-api.de` (429 under burst); `overpass.kumi.systems` works as fallback
- **User-Agent:** required
- **Method:** 30 km `around` search; distance to element **center** (approximate; production should use nearest point on way geometry)
- **Keep in payload:** `nearest_marine_km`, `nearest_inland_water_km`, `marine_feature`, `inland_feature`

### Sample results

| Label | Marine km / feature | Inland km / feature |
|-------|---------------------|---------------------|
| amazon_forest | none / null | 2.30 / **river** |
| london | 22.25 / **bay** | 0.08 / **water** |
| kansas | none / null | 0.48 / **water** |
| bergen_coast | 0.39 / **coastline** | 0.08 / **pond** |
| sahara | none / null | none / null |
| thames_riverside | 20.77 / **bay** | 0.21 / **river** |

### Implementation notes

1. **Rate limits:** serialize Overpass calls; retry on 429; consider `overpass.kumi.systems`
2. **London/Thames inland hits are huge** (10k+ ways in 30 km) — query is fine but production should compute true nearest geometry, not rely on center of mass for ranking
3. **`marine_feature`:** prefer `tags.natural` (e.g. `coastline`, `bay`) or `tags.place`
4. **`inland_feature`:** prefer `tags.waterway` (e.g. `river`, `canal`) else `tags.water` / `natural=water`
5. **Offshore nodata:** WorldCover transparent pixel → treat as `permanent_water` (not exercised in land samples)

---

## Locked fetch shape (for provider)

```python
{
    "land_cover_class": "built_up",
    "built_up_fraction": 1.0,  # fallback until GHSL
    "elevation_m": 7.0,
    "nearest_marine_km": 20.77,
    "marine_feature": "bay",
    "nearest_inland_water_km": 0.21,
    "inland_feature": "river",
    "solar_phase": "...",  # from BirthSeed, not fetched
}
```
