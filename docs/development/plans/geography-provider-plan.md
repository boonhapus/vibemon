# Geography / Biome Provider Plan (Draft)

## Goal
Add a second `VibeProvider` that derives a Vibemon's `Affinity` from the **physical place** of birth (land cover, terrain, ecosystem, human density) rather than the **sky above it**. Runs alongside `ClimateProvider`, never replaces it.

## Why a separate provider, not a climate extension
- Climate signals are *time-varying* (today's weather). Geography signals are *place-invariant* (a desert is a desert in January and July).
- Climate already overloads its 18 elements with weather proxies for habitat (e.g. POISON via pollution, ROCK via elevation). Geography can claim those habitats *directly* and free climate to focus on atmosphere.
- Two providers means a Vibemon born in a London fog is meaningfully different from one born in Hyde Park on the same foggy day. Geography supplies the *where*, climate supplies the *when*.
- Keeping providers single-source-of-truth simplifies replay, rate limiting, and signal calibration.

## Scope
- In scope:
  - New `app/providers/geography/` package mirroring `app/providers/climate/` layout.
  - One concrete `GeographyProvider` subclass of `VibeProvider`.
  - One external API client (recommendation below) with `LoggingHook` + `RateLimiterHook`.
  - `data/moves.json` of geography-flavored moves (terrain, structure, ecology).
  - Element scoring + stat mapping + intensity formula tuned for place, not weather.
  - Wiring into `rebalance_vibemon` workflow alongside `ClimateProvider`.
  - Tests under `vibemon/backend/tests/app/providers/geography/` using a fake API response fixture.
- Out of scope (v1):
  - Removing or rewriting any climate signal — climate stays untouched.
  - Cross-provider deconfliction (both may score the same element; downstream `filter_element_types` already handles ranking).
  - Caching layer (geography is place-invariant so a cache *would* pay off; defer until we measure).
  - User-facing copy explaining which provider produced what.

## Locked Product Decisions (proposed — open for review)
1. Geography is a **peer** of climate, not a fallback. Both run by default in `rebalance_vibemon`.
2. `name = "geography"`. Persisted in `Affinity.provider_id` so historical Vibemon remain attributable.
3. Provider must be **deterministic on replay**: `fetch()` returns enough raw payload that `synthesize()` can rerun without re-hitting the API.
4. Async like climate. Parallel-fetched in `BirthSeed.fetch_snapshot`.
5. One external API only in v1, chosen for free tier, no API key, and breadth of signal. Multi-source fusion is post-v1.
6. Six geography signals route to base stats. **Stat mapping must not duplicate climate's mapping** — they should feel complementary when combined.
7. Provider owns its own move pool. Move IDs prefixed `geography.*`. No shared moves with climate beyond `universal.*`.
8. Intensity for geography = "how distinctive is this place" (e.g. dense urban, deep wilderness, high alpine = 1.0; suburban field = 0.5).

## API Source — Recommendation

Three viable free sources; recommend **(A) Open-Meteo Geocoding + Elevation + OpenStreetMap Overpass**.

### Option A — OpenStreetMap Overpass API + Open-Meteo Elevation (recommended)
- **Signals available**: land use (residential/industrial/forest/farmland/water), nearest natural features (coast, lake, peak, cave, cliff, volcano), road density, building density, named amenities (graveyard, factory, hospital, library, dojo, shrine), elevation.
- **Pros**: free, no key, *enormous* coverage, direct habitat signals (graveyard → GHOST, factory → STEEL, library → PSYCHIC, dojo → FIGHTING — all the climate "semantic gaps" disappear).
- **Cons**: Overpass query language has a learning curve; response shape is heterogeneous; rate limits are advisory (1 req/sec, 10k elements).
- **Replay**: Overpass results are *not* perfectly stable (OSM edits drift). Snapshot the full response in `fetch()` payload so `synthesize()` is deterministic against the captured set.

### Option B — Mapbox Tilequery / Maps API
- **Pros**: clean JSON, fast, official land-cover tiles.
- **Cons**: requires API key, billed beyond 100k calls/month, tiles less semantically rich than OSM tags.

### Option C — GBIF + WorldClim + Natural Earth
- **Pros**: real species occurrence data (true BUG/GRASS/WATER signals from observed biodiversity).
- **Cons**: three sources to stitch; resolution coarse (~10km); response latency higher.

**Decision**: start with A. The semantic-gap closure (graveyard→GHOST, library→PSYCHIC) is the single biggest win and only A offers it for free.

## Element Mapping (proposed)

Geography reclaims habitat-grounded elements. Climate keeps atmosphere-grounded ones. Overlap is intentional (both score WATER) — downstream ranking picks the stronger signal.

| Element | Geography signal | Notes |
|---|---|---|
| NORMAL | residential / suburban land use | the baseline place |
| FIRE | volcano nearby OR industrial heat (steel works, refinery tagged) | climate keeps solar/heat |
| WATER | within Nkm of coast / lake / river / wetland | closes climate's "no proximity" gap |
| GRASS | forest / meadow / park / garden land cover | direct, not via humidity proxy |
| ICE | glacier feature OR permanent snow tag | direct |
| FLYING | elevation + open sky (low building density + no forest canopy) | shared with climate |
| FIGHTING | dojo / gym / stadium / quarry tags | closes climate's man-made gap |
| GROUND | desert / sand / bare rock land cover | direct |
| STEEL | factory / industrial / mine / construction tag | direct, not via pressure proxy |
| FAIRY | flower bed / botanical garden / pristine protected area | direct |
| POISON | landfill / sewage / heavy industrial cluster | direct, not via PM2.5 proxy |
| PSYCHIC | library / hospital / school / observatory | closes climate's "no signal" gap |
| DARK | urban density + low park ratio + night context | place-based shadow |
| GHOST | cemetery / abandoned building / ruins tag | closes climate's man-made gap |
| BUG | farmland / orchard / dense vegetation | direct |
| ROCK | cliff / cave / mine / mountain feature | direct |
| DRAGON | named peak above 3000m OR volcano + remoteness | direct |
| ELECTRIC | power plant / substation / dense urban grid | direct, not via CAPE proxy |

**Six chosen continuous signals routed to stats** (must not duplicate climate's mapping):

| Stat | Geography signal | Rationale |
|---|---|---|
| HP | population density (log-scaled) | mass / vitality of inhabited place |
| Attack | road / rail intersection density | infrastructure aggression |
| Defense | building density + nearest fortification | constructed solidity |
| Sp. Attack | amenity diversity (count of distinct cultural/scientific tags within radius) | informational density |
| Sp. Defense | green space ratio (parks + forest within radius) | natural cushion |
| Speed | distance to nearest transport hub (airport, port, major rail) | logistical reach |

Climate maps temperature, wind, elevation, radiation, precipitation, wind. Zero overlap.

## Architecture Overview
1. `BirthSeed` (already carries lat/lon, timestamp) is passed to both providers.
2. `GeographyProvider.fetch(seed)` issues:
   - Overpass query within ~3km radius of `seed.geo_coords` (radius tunable; document in code).
   - Open-Meteo elevation lookup (already used by climate — share or re-fetch? See open question).
3. Raw Overpass JSON + elevation snapshotted into payload dict.
4. `GeographyProvider.synthesize(seed, payload)`:
   - Parse OSM elements into `Signal` objects (reuse `app.providers.helpers.Signal` — its `ramp`/`mix` API maps cleanly onto density signals).
   - Run two-stage scoring identical in shape to climate: continuous block, then categorical bonuses keyed on dominant land-use tag.
   - Pick starter moves via same `_starter_move_weights` + `_pick_starter_moves` helper pattern.
   - Build `Affinity` with `provider_id="geography"`.
5. Wire into `rebalance_vibemon` defaults: `providers=(ClimateProvider(), GeographyProvider())`.

## File Layout

```
vibemon/backend/app/providers/geography/
├── __init__.py
├── api.py             # OverpassAPIClient(niquests.AsyncSession), elevation helper
├── const.py           # LandUseTag enum, AmenityTag enum, tier thresholds
├── provider.py        # GeographyProvider(VibeProvider)
└── data/moves.json    # geography-flavored move catalog
```

Mirrors climate exactly. No new abstractions.

## Data Model
**None.** Providers are stateless. `Affinity.provider_id` already exists. `BirthSnapshot` already stores per-provider payloads. No schema change required.

## Move Catalog Sketch
~30 moves, themes split by element. Examples (final list TBD):
- `geography.landslide` (ROCK, level 1)
- `geography.tidal_pull` (WATER, level 1)
- `geography.urban_decay` (POISON, level 5)
- `geography.cathedral_bells` (PSYCHIC, level 10)
- `geography.foundry_strike` (STEEL, level 5)
- `geography.grave_chill` (GHOST, level 1)
- `geography.summit_press` (DRAGON, level 20)

`universal.tackle` and `universal.breaking_point` reused (handled by base class loader).

## Testing Plan
### Unit
- `OverpassAPIClient` query construction (radius, tag filters, timeout).
- Tag parsing: dominant-land-use resolver given mixed element list.
- `determine_element_scores` against fixture payloads (urban / rural / coastal / alpine / industrial — one per archetype).
- `calculate_intensity` produces 1.0 for distinctive places, ~0.5 for suburb.
- Signal mapping covers all six stats with no division-by-zero on empty Overpass response.

### Integration
- Provider runs end-to-end against a captured Overpass response fixture.
- `BirthSeed.fetch_snapshot([ClimateProvider(), GeographyProvider()])` resolves both Affinities and both `provider_id`s persist.
- Replay determinism: same seed + same captured payload yields byte-identical Affinity.

### Regression
- Existing climate-only birth tests pass unchanged.
- `rebalance_vibemon` workflow tests pass with both providers wired in.

## Observability
- Reuse `LoggingHook` and `RateLimiterHook` from `app/providers/api_hooks.py`.
- Overpass rate limit: 1 req/sec, 10k elements/day per IP (conservative).
- Log Overpass query size and element count per fetch for tuning radius.

## Rollout
1. Land package + move catalog behind a flag (`SETTINGS.GEOGRAPHY_PROVIDER_ENABLED`, default off).
2. Add tests, fixtures, fakes.
3. Run shadow birth in dev: both providers fetch, only climate's Affinity is persisted, geography's is logged for inspection.
4. Tune element thresholds against shadow output across 50+ varied coordinates.
5. Flip flag in staging; verify replay parity.
6. Production rollout with flag.
7. Document provider in CONTEXT.md vocabulary section.

## Open Questions
1. **Radius**: 1km, 3km, or adaptive (urban=500m, wilderness=10km)? Affects what "place" means for a coordinate at a city park edge.
2. **Elevation duplication**: climate already fetches elevation from Open-Meteo. Share via `BirthSnapshot` payload, or re-fetch independently? Sharing couples providers; re-fetching wastes a call. Lean toward re-fetch for provider independence.
3. **Stat-mapping overlap risk**: do we want zero overlap (current proposal) or partial overlap with averaging? Zero overlap maximizes flavor differentiation; partial overlap smooths edge cases.
4. **Intensity composition**: when both providers run, does the persisted Vibemon's `intensity` come from one provider, the max, or a blend? Current `Affinity` has a single `intensity` field — does it become per-provider, or do we add an aggregation rule?
5. **Move pool size**: climate has N moves; geography should be comparable to keep starter-pool sampling balanced. Final count TBD after move design pass.
6. **Overpass downtime**: public Overpass instances go down. Fallback policy — fail the birth, retry later, or birth with climate-only? Climate already does HTTP retry; geography should match.

## Notes for Future Expansion
- Add GBIF species-observation enrichment for true biodiversity signals (BUG, GRASS).
- Add Natural Earth ecoregion tagging for biome classification independent of OSM coverage gaps.
- Self-host an Overpass mirror if traffic justifies (removes the public-instance dependency).
- Geography is a natural fit for caching by geohash precision-7 (~150m) since signals are stable over weeks/months — defer until cache hit rate measured.
