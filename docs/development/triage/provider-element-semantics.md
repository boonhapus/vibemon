# Provider element semantics

**Status:** open — design triage, no code changes yet  
**Recorded:** 2026-06-02  
**Scope:** `ClimateProvider` element scoring, move catalog, and Open-Meteo signals; cross-provider ownership when more providers ship

---

## Principle

Each **VibeProvider** should expose only element types it can justify from **its own data domain** with a tight, literal mapping. Flavor text and move names can be poetic; **scoring logic and `exposed_elements` blurbs must not pretend the API sees places or concepts it cannot observe** (cemeteries, farms, coastlines, “night” without time-of-day, fairy groves without flora).

When multiple providers participate in birth synthesis:

- **Own** an element where your signals are the primary, unambiguous source.
- **Share** an element only when signals are genuinely complementary (e.g. biome land cover + climate precipitation), not duplicate proxies.
- **Trim** elements (and their 15-move learnset slices, scoring blocks, and orphan raw fields) from a provider once another provider owns that semantics better.

Today: **climate** (sky/time-series weather), **biome** (land cover, water proximity, solar phase), **music** (listening/tags/audio). Climate exposes **16** types; biome **18** (adds Steel, Psychic); music **18** (adds Steel, Psychic; different Electric/Dark split).

This doc records **stretch** (mapping weaker than the data domain), **gap** (data exists elsewhere but not here), and a **future trim matrix** per provider. Execute trims only after multi-provider birth compositing is defined so dropped types can still surface from sibling providers.

---

## Climate provider — signal inventory

Open-Meteo forecast + air-quality, birth-day index `i = -1`, WMO `weather_code` bonuses.

| Signal key | Source field | Used for |
| --- | --- | --- |
| `cape_m` | `cape_mean` | Sp. Attack mix, Dragon, Electric |
| `clouds` | `cloud_cover_mean` | Flying penalty, Dark |
| `dew_pt` | `dew_point_2m_mean` | Grass |
| `dust_m` | `dust_mean` (AQ hourly → daily) | Ground, Fighting impact |
| `elevat` | `elevation` | Ice, Flying, Rock, Dragon |
| `transp` | `et0_fao_evapotranspiration` | Grass, Bug |
| `pollut` | `pm2_5_mean` (AQ hourly → daily) | Defense mix, Poison, Dark, Fairy veto |
| `precip` | `precipitation_sum` | Water, Fighting, Ground gate |
| `humdty` | `relative_humidity_2m_mean` | Fire arid, Poison swamp, Ground, Bug, Fairy mist |
| `radiat` | `shortwave_radiation_sum` | Fire, Sp. Attack mix |
| `snowfl` | `snowfall_sum` | Ice, Rock veto |
| `tmp_hi` / `tmp_lo` | temperature max/min | Fire, Ice, Bug, Ghost chill, intensity |
| `uv_idx` | `uv_index_max` | Fairy, Ghost, Dark |
| `visibl` | `visibility_mean` | Defense obscurity, Fighting, Ghost, Dark |
| `windgu` / `windsp` | gust / speed max | Attack, Fighting vs Flying, Poison still air |

Base stats (not elements): HP ← temps; Attack ← gusts; Defense ← obscurity + pollution; Sp. Atk ← radiation + CAPE; Sp. Def ← humidity + precip; Speed ← sustained wind.

---

## Climate element fit (current)

| Element | `exposed_elements` claim | What code actually uses | Stretch |
| --- | --- | --- | --- |
| Fire | Solar radiation / extreme heat | `radiat`, `tmp_hi`, arid `humdty` | Low |
| Water | Precipitation | `precip` + WMO rain/drizzle only | **Gap** (not stretch): no coast/lake — see below |
| Grass | ET₀ or dew point | `transp`, `dew_pt` | Low |
| Ice | Cold / snow | `tmp_lo`, `snowfl`, elev factor + WMO snow | Low |
| Flying | Sustained wind 15+ km/h | `windsp`, `elevat`, `clouds` clear-sky factor | Low |
| Fighting | Gust spikes, impact weather | Gust excess vs `windsp`, dust / visibility / heavy precip | Low (deliberate split from Flying) |
| Ground | Dust / arid earth | `dust_m`, dry precip gate, low humidity | Low |
| Electric | Thunderstorms | `cape_m` + WMO thunder/hail (no urban grid) | Low |
| Normal | Overcast, no precip | `0.3 × (1 − max scores)` + WMO overcast | Low (baseline “bland day”) |
| Fairy | UV radiation | Clean air × (`uv_idx` sun or humid haze); WMO clear +0.2 | **High** — UV/haze ≠ fairy ecology |
| Dark | Low visibility / overcast | Pairwise `uv_idx` ↓, `clouds`, `pollut` | **High** — low UV ≠ night/cemetery |
| Ghost | Fog, low UV | `visibl`, `uv_idx`, chill; WMO fog +0.5 | **Medium** — fog OK; graveyard lore not in data |
| Bug | Humid tropical heat | `humdty`×`tmp_hi` or `transp`×`tmp_hi` | **Medium** — overlaps Grass; no insects/habitat |
| Poison | Air pollution | `pollut` OR swamp proxy (humid×warm×still) | **Medium** — PM₂.₅ solid; swamp path is proxy |
| Rock | Elevation / hail | `elevat` with ice veto; hail via WMO | **Low–medium** — elevation ≠ geology |
| Dragon | CAPE | `sqrt(cape × elevation)` only; no lowland storm WMO Dragon bonus | **Medium** — physics label, strict logic is fine |

### Documented gap (keep or defer to biome)

**Water:** Comments in `determine_element_scores` state Open-Meteo has no water-proximity field; coastal/lakeside birth does not read Water from climate alone. Biome already scores `WATER` from OSM/Overpass marine and inland distance. Do not “fix” with a stretched climate proxy — trim or narrow climate Water to **precip-only** labeling and let biome own standing water.

### Correlation risk

**Ghost** and **Dark** share visibility, UV, and pollution pathways. Dark’s pairwise gate and Ghost’s fog WMO bonus reduce collisions but gloomy polluted winter days can still double-fire. Future pass: assign **gloom/smog** primarily to one provider or one element.

---

## Biome provider — signal inventory

ESA WorldCover 2021 (Terrascope raster), Open-Meteo elevation point, OSM Overpass water proximity, plus **`solar_phase` from `BirthSeed`** (not a terrain API — time-of-birth at coordinates).

| Signal / field | Source | Used for |
| --- | --- | --- |
| `land_cover_class` | WorldCover RGB → `WorldCoverClassT` | Per-class `base_weights`, stat archetype, `water_proximity_gate`, flavor |
| `built_up_fraction` | 1.0 if class is `built_up`, else 0.0 | Urban vs `NATURAL_ELEMENT_WEIGHTS`; urban stat nudges |
| `elevation_m` | Open-Meteo elevation | `HIGH_ELEVATION_ELEMENT_WEIGHTS`; Defense/Speed stat nudges |
| `nearest_marine_km`, `marine_feature` | Overpass (coastline, bay, …) | Water score × gate; marine feature bonuses |
| `nearest_inland_water_km`, `inland_feature` | Overpass (river, canal, lake, …) | Water score × gate; inland/lake bonuses; built-up “canal frontage” |
| `solar_phase` | `BirthSeed` | `SOLAR_PHASE_BONUS` (Fairy/Psychic dawn; Ghost dusk/night; Dark night; Fire/Flying day) |

Base stats: land-cover archetype tiers + urbanity (Speed/Sp. Atk ↑, HP/Sp. Def ↓) + elevation (Defense ↑, Speed ↓). Water fetch failures degrade to `None` distances (logged); scoring continues without water proximity.

---

## Biome element fit (current)

| Element | `exposed_elements` claim | What code actually uses | Stretch |
| --- | --- | --- | --- |
| Grass, Bug, Water, Fire, Ground, Rock, Ice | Land cover + water + elevation | `WORLD_COVER_PROFILES`, proximity, `HIGH_ELEVATION_*` | Low |
| Steel, Electric, Dark | Built-up fabric | `BUILT_UP` base + `URBAN_ELEMENT_WEIGHTS`; Dark also night `SOLAR_PHASE_BONUS` | Low (Electric = urban grid metaphor, not weather lightning) |
| Normal | Grassland, cropland, suburban open | Per-class weights + `0.2 × (1 − max scores)` | Low |
| Poison | Wetlands, industry, stagnant water | `HERBACEOUS_WETLAND` / `MANGROVES` + urban Poison | **Medium** — two stories (swamp vs smog); climate owns PM₂.₅ when linked |
| Flying | Open grassland, high elevation | Grassland base + `HIGH_ELEVATION` Flying weight | **Medium** — “thin air / vista,” not wind (climate owns wind) |
| Fighting | Shrubland badlands | **Only** `SHRUBLAND` base 0.30; loses to Ground/Fire on same class | **High** — rarely primary; catalog filler |
| Ghost | Tree shade, built-up “historical footprint” | `TREE_COVER` 0.35 + dusk/night solar; **no** built-up Ghost weight | **Medium** — shade/fog-adjacent OK; “historical footprint” not in scoring |
| Dragon | High wilderness, isolated terrain | **Only** `HIGH_ELEVATION_ELEMENT_WEIGHTS` 0.20 × elev signal | **High** — mountain-dragon trope; moves are alpine geology (Rock/Ground flavor) |
| Fairy | Moss/lichen, dawn/dusk | `MOSS_LICHEN` 0.30 + dawn/dusk solar | **High** — lichen → fairy is poetic; overlaps dawn “mood” with Psychic |
| Psychic | Dawn stillness, forest/open | **Only** dawn `SOLAR_PHASE_BONUS` 0.15 | **High** — no land-cover path; time-of-day, not terrain |
| Water (proximity) | Rivers, coast, wetlands | OSM distances + gates; tests assert forest/grass **identity** beats nearby river | Low for *trim*; keep precip vs proximity split with climate |

### Catalog vs scoring stretch

Biome exposes **all 18** types with **15 moves each** (`test_biome_move_catalog_has_fifteen_moves_per_exposed_element`). Several types exist mainly for catalog completeness while scoring makes them **unlikely or impossible as primary identity** (notably **Psychic**, **Dragon**, **Fighting**). That is structural stretch: flavor moves without a strong scoring path.

### Cross-provider overlap (biome ↔ climate ↔ music)

| Element | Biome | Climate | Music | Risk |
| --- | --- | --- | --- | --- |
| Water | OSM proximity, permanent water class | Precip + WMO rain only | Downtempo / fluid tags | **Complementary** if labels stay honest |
| Ice | Snow/ice cover, cold elev | Temp, snowfall | Minimal techno | Complementary |
| Dragon | Elev wilderness | CAPE × elev | Epic metal | **Duplicate mythic** — pick one primary owner |
| Ghost / Dark | Shade, night urban | Fog/UV/gloom | Dark ambient, goth, valence dim | **Triple overlap** on “gloomy”; music valence/key nudges amplify |
| Fairy | Moss + dawn/dusk | UV (stretch) | K-pop, bright valence, major key | **Duplicate “sparkle”**; trim climate/biome, keep music |
| Psychic | Dawn only | *(omitted)* | Classical, jazz, gospel, spoken | Biome weakest; **music primary owner** |
| Poison | Wetland + urban | PM₂.₅ + swamp proxy | Harsh electronic | Split industrial vs swamp |
| Flying | High elev | Wind | Shoegaze | Split physics vs genre |
| Fighting | Shrubland only | Gust/dust impact | Punk/hardcore | Music >> biome for Fighting |
| Electric | Built-up | Thunder CAPE | Dance/electro | Split grid vs storm vs genre |
| Steel | Built-up industrial | *(omitted)* | Metal tags | Biome + music; climate correctly omits |

### Borrowed signal: `solar_phase`

Solar phase is **not** observed by WorldCover/elevation/Overpass. It is defensible narratively (“born at this place at this moment”) but blurs biome’s “ground beneath” premise. **Psychic**, **Fairy**, **Ghost**, and **Dark** night bonuses depend on it — prime candidates to **trim from biome** and leave to a future **celestial** or **moment-of-birth** provider, or to climate/music where semantics match.

---

## Music provider — signal inventory

Last.fm `user.getTopTracks` (7-day + 1-month windows), MusicBrainz recording lookup/search, ReccoBeats `audio-features` (ISRC or Spotify ID). Element scoring runs on **`payload.tracks` only** — tracks that failed ReccoBeats enrichment are dropped entirely (genres/tags on those tracks do not contribute).

| Signal / layer | Source | Used for |
| --- | --- | --- |
| `plays` | Last.fm playcount | Weight for all tag rules and valence/key nudges |
| `genres`, `tags` | MusicBrainz recording | `classify_genre.json`, `classify_mood.json`, `classify_instrument.json` (regex rules) |
| `valence` | ReccoBeats | Per-track brightness nudge → Fairy/Normal/Electric vs Ghost/Dark/Water/Psychic |
| `mode` (`is_major_key`) | ReccoBeats | Per-track major vs minor nudge (same type buckets as valence, partially overlapping) |
| `last7d`, `last1m` | Last.fm aggregate play totals | `calculate_intensity` (7-day vs prior-23-day pace on `Affinity.intensity`, not elements) |
| `tempo`, `duration`, `loudness`, `energy`, `acousticness`, `instrumentalness`, `danceability`, `liveness`, `speechiness` | ReccoBeats | `derive_signals` → `balance_for_bst` (HP, Atk, Def, SpA, SpD, Spe) |

Classify data: **30** genre families, **13** mood rules, **12** instrument rules (`tests/app/providers/music/test_classify.py`). Catalog: **18** exposed types × **15** moves each (`test_music_move_catalog_has_fifteen_moves_per_exposed_element`).

### Structural mismatch (doc vs code)

`MusicProvider` docstring claims typing uses labels **“across every resolved track.”** In practice `fetch` → `ensure_full_track` keeps only ReccoBeats-resolved rows; `synthesize` → `determine_element_scores` sees **`payload.tracks` only**. Thin ISRC/Spotify coverage therefore thins **both** base stats **and** element tags (warning `music.thin_stat_coverage` when <50% of parsed tracks have audio). Future fix options: score tags from `TrackInfo` before ReccoBeats filter, or relabel the docstring to “ReccoBeats-covered tracks only.”

---

## Music element fit (current)

| Element | `exposed_elements` claim | What code actually uses | Stretch |
| --- | --- | --- | --- |
| Normal | Pop, neutral tags, bright valence | `pop` rule; valence/major nudges; fallback when no scores | Low |
| Fire | Rock/metal/electronic/latin energy | Genre secondaries + mood `energetic` | Low |
| Water | Fluid/ambient/downtempo + subdued valence | `rnb_soul_funk`, `reggae_ska`, valence dim branch | **Medium** — soul/funk/reggae → Water is poetic, not literal |
| Grass | Folk, acoustic, singer-songwriter | `folk`, `indie_alternative` partial, instrument `acoustic` | Low |
| Ice | Minimal techno, microhouse | `minimal` rule; mood `cold` | **Medium** — “crystalline repetition” metaphor |
| Flying | Shoegaze, dream pop, ethereal | `flying` rule; mood `dreamy`; instrument flute | **Medium** — ethereal ≠ aerial; overlaps `space rock` in `rock` rule |
| Fighting | Punk, hardcore, aggressive hip-hop | `punk` rule; instrument drums | Low for punk; **high** if drums alone fire |
| Poison | Noise, industrial, harsh electronic | `noise_industrial`; `experimental` partial | **Medium** — harsh *sound* as toxic, not thematic poison |
| Ground | Roots, blues, Americana | `blues`, `country`, instrument guitar/bass | Low for blues/country; **medium** for guitar → Ground |
| Bug | Hyperpop, glitch, buzzing microgenres | `microgenre`, `experimental` partial | **High** — deliberate digital-insect metaphor; vaporwave sits here vs Ghost |
| Rock | Classic/alt/guitar-forward | `rock`, `indie_alternative` (primary Rock weight) | Low — note metal/punk listeners often score Steel/Fighting, not Rock |
| Ghost | Dark ambient, dungeon synth, low valence | `spectral`, valence dim, minor key, mood `nostalgic` | **Medium** — fog/nostalgia OK; overlaps Dark |
| Dragon | Power metal, symphonic, epic scores | `progressive`, `stage_screen`, `classical` partial, mood `epic` | **Medium** — epic scale mythic; overlaps climate CAPE Dragon |
| Electric | Synthpop, electro, dance | `electronic` rule (broad) | Low |
| Dark | Goth, darkwave, minor melancholy | `dark` genre, valence dim, minor key | **Medium** — minor key on sad pop is reductive |
| Steel | Metal, industrial rock | `metal` primary; noise partial | Low for metal; **medium** for “industrial rock” blurb vs Poison/industrial tags |
| Fairy | K-pop, sparkly pop, bright valence, major keys | `sparkle`, `pop` partial, `childrens`, valence/major nudges | **Medium** — k-pop lives under `pop` → Normal primary; UV-style “sparkle” is music-native |
| Psychic | Classical, jazz, contemplative, minor depth | `classical`, `jazz`, `religious`, `spoken`, minor partial | **High** — catch-all for “smart/spiritual”; gospel → Psychic vs organ → Ghost |

### Global nudges (systemic stretch)

Applied **per track** on top of genre/mood/instrument hits — can swamp tag signal:

- **Valence** → Fairy/Normal/Electric (bright) or Ghost/Dark/Water/Psychic (dim), scaled by `plays × 0.25`.
- **Major/minor** → Fairy/Electric/Normal vs Dark/Ghost/Psychic, scaled by `plays × 0.25`.

These ignore genre context (e.g. minor-key power metal, major-key goth pop). Highest-leverage tightening in a future pass: lower weights, gate on genre miss only, or drop key nudge entirely.

### Intentional metaphor buckets (keep or trim consciously)

Documented flavor mappings — fine for a game, weak as “semantic ownership”:

| Element | Genre / tag hook | Metaphor |
| --- | --- | --- |
| Bug | hyperpop, glitch, vaporwave | Digital buzzing |
| Ice | minimal techno, microhouse | Crystalline / cold repetition |
| Flying | shoegaze, dream pop | Ethereal / spacey |
| Poison | noise, power electronics | Harsh / toxic sound |
| Dragon | prog metal, soundtracks, orchestral | Epic scale |

### Instrument tag rules (weak adjunct)

`classify_instrument.json` adds small weights (0.2–0.4 × plays) for single-token tags: piano → Psychic, drums → Fighting, organ → Ghost, flute → Flying, etc. Easy false positives on generic MB tags (`string`, `keyboard`, `digital`). **Trim candidate:** drop instrument layer entirely and rely on genre + mood only.

### Catalog vs scoring

Music exposes **all 18** types with **15 moves each**. **Steel** is almost entirely `metal` genre; **Rock** primary only from `rock` / `indie_alternative` (not from metal or punk). **Psychic** has strong genre paths but overlaps biome’s dawn-only Psychic and climate’s omission. Moves are on-theme; stretch is in **scoring**, not move names.

---

## Future pass — trim / relocate matrix

Use when birth composes **multiple providers** and we want non-overlapping semantic ownership.

**Per-provider trim** = remove from `exposed_elements`, delete **15 moves per type** in `{provider}/data/moves.json`, drop scoring blocks (and WMO/weight tables), and remove **raw fetch fields** only referenced by that block. Re-run provider-balance-analysis and update `test_*_move_catalog_has_fifteen_moves_per_exposed_element`.

### Climate

| Element | Recommendation | Rationale | Prefer owner | Climate artifacts to remove |
| --- | --- | --- | --- | --- |
| **Fairy** | **Trim from climate** | No floral/enchanted signal; UV is a weak type mapping | Biome (`moss/lichen`, dawn/dusk solar); music (bright pop/valence) | `exposed_elements` FAIRY; scoring block + CLEAR_SKY FAIRY bonus; 15× fairy moves; **`uv_idx` signal** if nothing else needs it |
| **Dark** | **Trim or narrow** | Low UV + cloud + smog is “gloomy sky,” not Dark fantasy | Biome (built-up + `SolarPhase` night); music (goth/darkwave) | Full Dark block + overcast DARK bonus; 15× dark moves; keep `pollut` for Poison/Defense |
| **Ghost** | **Keep climate-only if trimmed Dark overlap** else **trim** | Fog/rime WMO is authentic; shade/graveyard is biome | Climate for **fog/low visibility** OR biome tree-shade; not both at full weight | If trimmed: GHOST block, fog WMO +0.5, 15× ghost moves; **`visibl`** only if unused elsewhere |
| **Bug** | **Trim from climate** | Humidity×heat and ET₀ duplicate Grass | Biome (tree/crop/mangrove) | BUG block; 15× bug moves; **`transp` Bug path** (keep for Grass) |
| **Poison (swamp path)** | **Narrow, not full trim** | Keep **PM₂.₅**; drop swamp composite | Biome wetlands + industrial | Remove `swamp_humidity` × `swamp_warmth` × `still_air_factor` branch only |
| **Rock** | **Narrow** | Hail WMO + peaks OK; continuous elev-only is biome’s job | Biome bare rock / high elev | Continuous `elevat` ROCK score; keep WMO hail ROCK bonuses; optional trim of 15 rock moves if biome owns ROCK entirely |
| **Dragon** | **Keep (strict)** | Rare `sqrt(cape × elev)` is intentional | Climate only for **convective mountain** mythic | Do not re-add lowland thunderstorm Dragon WMO bonus (already removed in code comments) |
| **Water** | **Keep precip-only** | Semantic honesty | Biome for proximity; climate for **rain/snow codes** | Relabel `exposed_elements` to precip-only; do not add fake coastal scoring |
| **Steel / Psychic** | **Already omitted** | Correct — no weather semantics | Biome Steel; **music** Psychic (biome Psychic slated for trim) | None |

### Signals safe to drop after trims (climate-only)

Only if no scoring/base-stat path references them:

| Signal | After trim |
| --- | --- |
| `uv_idx` | Removable if Fairy, Ghost, Dark scoring all gone or rewritten without UV |
| `transp` (partial) | Keep for Grass; Bug branch removed |
| `visibl` | Keep if Fighting, Ghost, Defense obscurity, intensity remain |

Air-quality fetch (`pm2_5`, `dust`) stays if Poison/Ground/Fighting/Defense still use them.

### Biome

| Element | Recommendation | Rationale | Prefer owner | Biome artifacts to remove |
| --- | --- | --- | --- | --- |
| **Psychic** | **Trim from biome** | Only dawn `SOLAR_PHASE_BONUS` 0.15; no terrain signal | Music (contemplative tags); future celestial / chronobiology provider | `exposed_elements` PSYCHIC; `SOLAR_PHASE` Psychic dawn line; 15× psychic moves; **`solar_phase` on payload** only if no other biome type needs phase |
| **Dragon** | **Trim from biome** | Elev weight 0.20 only; moves read as Rock/Ground alpine | Climate (`sqrt(cape × elev)`); music (epic metal); **or** compositor capstone rule | `HIGH_ELEVATION` Dragon entry; 15× dragon moves; relabel strongest elev moves to Rock if kept |
| **Fighting** | **Trim from biome** | Single shrubland hook; never wins vs Ground/Fire | Music (punk/hardcore); climate (gust/dust impact) | `SHRUBLAND` Fighting weight; 15× fighting moves |
| **Fairy** | **Trim or narrow** | Moss/lichen + solar phase is weak; climate Fairy also slated for trim | Music (k-pop, bright valence); optional future flora provider | Full Fairy block + dusk/dawn Fairy solar lines; 15× fairy moves; keep moss as **Grass/Normal** flavor only |
| **Ghost** | **Narrow** | Tree shade OK; “historical footprint” blurb false for built-up | Climate fog **or** biome shade — not both at full weight | Drop built-up blurb; optionally trim Ghost if climate keeps fog Ghost; 15× ghost moves if trimmed |
| **Dark** | **Narrow** | Built-up + night phase overlaps music goth and climate gloom | Music + built-up **without** night if `solar_phase` leaves biome | Night `SOLAR_PHASE` Dark bonus; relabel to “dense urban fabric” only |
| **Flying** | **Narrow** | High elev ≠ flight | Climate wind; music shoegaze | Remove Flying from `HIGH_ELEVATION_ELEMENT_WEIGHTS`; keep grassland open-sky if any |
| **Poison (urban)** | **Narrow** | Wetland Poison is authentic | Climate PM₂.₅ for smog; biome wetland/industrial split | Drop `URBAN_ELEMENT_WEIGHTS` Poison or built-up Poison base if climate linked |
| **Electric** | **Keep (urban)** | Built-up is literal | Climate thunder stays separate (storm, not grid) | None |
| **Steel** | **Keep** | Built-up industrial | Music metal is genre, not geography | None |
| **Water** | **Keep** | Core domain (OSM + permanent water class) | Climate precip only | None |
| **Grass, Bug, Ground, Fire, Rock, Ice, Normal** | **Keep** | Direct WorldCover + elev + water | — | None |

### Music

Execute **after** multi-provider compositor is defined. Music should remain the **primary mood/genre owner** for types trimmed from biome/climate. When trimming music, ensure sibling providers can still surface those types in combined birth.

| Element | Recommendation | Rationale | Prefer owner | Music artifacts to remove |
| --- | --- | --- | --- | --- |
| **Psychic** | **Keep (primary)** | Jazz/classical/spoken are music-native; biome Psychic slated for trim | Music; future celestial if chronobiology added | None unless compositor caps duplicate Psychic across providers |
| **Fairy, Dark, Ghost** | **Keep (primary)** | Genre + valence paths; climate Fairy/Dark and biome Fairy/Ghost slated for trim | Music | None; **narrow** valence/key weights instead of full trim |
| **Fighting** | **Keep** | Punk/hardcore; absorbs biome Fighting trim | Music | Drop instrument `drums` rule if false positives matter |
| **Dragon** | **Keep or capstone-only** | Epic metal/soundtracks; overlaps climate CAPE Dragon | **Pick one** mythic owner (music **or** climate) | If capstone: trim `progressive`/`stage_screen` Dragon weights + 15× dragon moves |
| **Bug, Ice, Flying, Poison** | **Keep or narrow** | Intentional metaphors; not observable elsewhere | Music only for these microgenre buckets | If trimmed: delete `microgenre`, `minimal`, `flying`, `noise_industrial` rule blocks + 15× moves each; relabel moves to adjacent types |
| **Steel** | **Keep** | Metal genre is literal tag mapping | Music (genre); biome (industrial built-up) | None |
| **Rock** | **Keep** | Guitar-forward genres | Music | None |
| **Water** | **Narrow** | Keep ambient/downtempo **tags**; drop soul/funk/reggae → Water if stretch bothers | Biome (proximity); music (fluid **mood** only) | Remove or split `rnb_soul_funk` Water primary; adjust valence dim Water share |
| **Ground** | **Keep** | Blues/country | Music | Trim instrument `guitar`/`bass` → Ground if redundant with genre |
| **Electric, Fire, Grass, Normal** | **Keep** | Core listening semantics | — | None |
| **Rock vs Steel vs Fighting** | **Clarify blurbs** | Listeners may never see Rock primary if catalog is metal/punk-heavy | — | Update `exposed_elements` only; no trim required |

#### Valence / key / instrument (raw scoring layers)

| Layer | Recommendation | Rationale | Artifacts to remove |
| --- | --- | --- | --- |
| **Valence nudge** | **Narrow** (lower `0.25` scale or gate on unclassified labels) | Swamps genre signal | `determine_element_scores` brightness branches in `music/provider.py` |
| **Major/minor nudge** | **Trim or narrow** | Reductive harmonic typing | `is_major_key` branch; optional drop of `mode` from `Track` if unused elsewhere |
| **Instrument rules** | **Trim optional** | Coarse MB tags | `classify_instrument.json`; instrument loop in `determine_element_scores`; tests in `test_classify.py` |
| **Mood rules** | **Keep** | Complements genre | None |
| **Genre rules** | **Keep** (edit weights) | Core domain | Per-family edits in `classify_genre.json` only |

#### Fetch / payload (raw data points)

| Field / step | Recommendation | Notes |
| --- | --- | --- |
| ReccoBeats-only `payload.tracks` for **elements** | **Fix or document** | Score `TrackInfo` tags pre-audio, or update docstring |
| `last7d` / `last1m` | **Keep** | Intensity only |
| Last.fm 7-day top tracks fetch | **Keep** | Intensity input; not used for element tags today |
| MusicBrainz search/rank | **Keep** | Required for tags + ISRC |
| `classify_*.json` | **Keep** | Trim = delete rule entries, not whole files unless layer removed |

### Cross-provider — who should own what (target)

| Element | Primary owner | Secondary (optional) | Trim from |
| --- | --- | --- | --- |
| Water (standing/coast) | Biome | Climate (precip) | — |
| Water (rain event) | Climate | — | Biome “rain” flavor in moves only |
| Psychic | Music (classical, jazz, spoken) | Celestial (future) | **Biome** |
| Fairy | Music (pop, valence, sparkle) | — | **Biome**, **Climate** |
| Dragon | Climate **or** Music (pick one mythic) | Compositor capstone | **Biome**; do not triple-weight |
| Ghost | Climate (fog) **or** Biome (forest shade) | Music (dark ambient, low valence) | One of climate/biome at full weight; music keeps genre Ghost |
| Dark | Music (goth, darkwave, minor key) | Biome urban night (if `solar_phase` stays) | **Climate** |
| Fighting | Music (punk, hardcore) | Climate impact | **Biome** |
| Poison (smog) | Climate | Biome industrial | Narrow biome/climate swamp duplicate; **music** owns harsh electronic Poison |
| Poison (swamp) | Biome | — | Climate swamp proxy |
| Flying (wind) | Climate | Music (shoegaze / ethereal) | Biome elev Flying |
| Electric (storm) | Climate | — | — |
| Electric (city/grid) | Biome | Music (dance, electro) | — |
| Steel | Biome (industrial) | Music (metal tags) | — |
| Bug | Music (glitch/hyperpop) | Biome (habitat) | **Climate** Bug |
| Grass | Biome | Music (folk/acoustic) | — |
| Rock | Music (guitar genres) | Biome bare rock | Climate elev Rock (narrow) |
| Ground | Biome + Music (blues/country) | Climate dust | — |
| Water (standing) | Biome | — | — |
| Water (fluid mood) | Music (narrow) | Climate precip | Trim music soul/funk → Water if needed |
| Ice | Biome + Climate | Music (minimal techno metaphor) | — |
| Fire | Climate + Music | Biome scrub | — |
| Normal | All providers (baseline) | — | — |

### Signals safe to drop after trims (music-only)

| Artifact | After trim |
| --- | --- |
| `classify_instrument.json` + instrument scoring loop | Removable if genre + mood suffice |
| `mode` / `is_major_key` on `Track` | Removable if major/minor nudge dropped |
| Valence branches in `determine_element_scores` | Removable or reduced if mood rules cover brightness |
| Genre rule families (`microgenre`, `minimal`, `flying`, `noise_industrial`, …) | Remove file entries + 15× moves per dropped **element** |
| ReccoBeats feature fields | Keep for base stats unless provider shrinks to tags-only stats |

Last.fm + MusicBrainz fetch paths stay unless music provider is retired.

### Signals safe to drop after trims (biome-only)

| Field / table | After trim |
| --- | --- |
| `solar_phase` on `BiomePayload` | Removable if Fairy, Psychic, Ghost, Dark solar bonuses all removed from biome |
| `SOLAR_PHASE_BONUS` | Drop entire map or keep **day** Fire/Flying only if phase stays for minimal “moment” flavor |
| `HIGH_ELEVATION_ELEMENT_WEIGHTS` Dragon (and optionally Flying) | Keep Rock, Ice; trim mythic/altitude-flight |
| Overpass fetch | **Keep** unless Water trimmed entirely (unlikely) |
| `URBAN_ELEMENT_WEIGHTS` Poison | Drop if smog lives only on climate |

---

## Strong climate-native set (target end state)

If the trim pass runs, climate should anchor roughly **10–12** high-confidence types:

| Keep | Why |
| --- | --- |
| Fire, Ice, Water (precip), Grass, Electric | Direct weather physics |
| Flying, Fighting | Wind profile split |
| Ground | Dust + aridity |
| Normal | Anti-extreme baseline |
| Dragon (optional rare) | Strict CAPE × elevation |
| Ghost **or** Dark **or** neither | Pick at most one “obscured sky” element unless compositor merges provider scores |

Everything else is candidate for **biome**, **music**, or a future provider (e.g. celestial, urban) with domain-appropriate data.

---

## Strong biome-native set (target end state)

If the trim pass runs, biome should anchor roughly **12–14** high-confidence types tied to **observed land/water/elev**:

| Keep | Why |
| --- | --- |
| Grass, Bug, Water, Fire, Ground, Rock, Ice | WorldCover + water proximity + snow/elev |
| Steel, Electric | Built-up literal |
| Normal | Baseline / open land |
| Poison | **Wetland + mangrove** (narrow urban Poison if climate not linked) |
| Dark | **Optional** — only if kept as “dense urban” without solar night; else music |
| Ghost, Fairy, Psychic, Dragon, Fighting | **Trim** — weak or absent scoring paths |
| Flying | **Trim or narrow** — defer wind to climate, genre to music |

Dropped types should still appear in **combined birth** via music (and climate for weather-native types).

---

## Strong music-native set (target end state)

If the trim pass runs, music should anchor roughly **14–16** types with **honest tag/audio ownership**, plus optional metaphor types kept deliberately:

| Keep (high confidence) | Why |
| --- | --- |
| Normal, Fire, Grass, Ground, Rock, Electric, Fighting, Steel | Direct genre families |
| Dark, Ghost, Fairy, Psychic | Mood/genre owner after biome/climate trims |
| Electronic dance stack | `electronic` rule is broad but domain-native |

| Keep (metaphor — explicit) or trim | Why |
| --- | --- |
| Bug, Ice, Flying, Poison | Game metaphor; trim only if compositor dedupes with biome/climate |
| Dragon | Epic genre; **one** provider should own mythic with climate |

| Narrow (layers, not necessarily elements) | Why |
| --- | --- |
| Valence / major-minor nudges | Systemic stretch |
| Instrument rules | Weak MB tag signal |
| Water (soul/funk/reggae) | Poetic stretch — keep ambient/downtempo only |

| Fix (structural) | Why |
| --- | --- |
| Tag scoring on all MB-resolved tracks | Doc claims “every resolved track”; code uses ReccoBeats subset |

---

## Implementation checklist (when executing trim)

### Climate

1. Update `ClimateProvider.exposed_elements` and `determine_element_scores` (+ WMO `match` arms) in `vibemon/backend/app/providers/climate/provider.py`.
2. Remove move entries from `vibemon/backend/app/providers/climate/data/moves.json` (15 per dropped type); run provider-balance-analysis / move-generator quotas.
3. Adjust `derive_signals` / `fetch` air-quality merge only if a signal becomes unused project-wide in that provider.
4. Update `tests/providers/test_climate_provider.py` (`15 moves per exposed element` assertion).

### Biome

1. Update `BiomeProvider.exposed_elements` and `determine_element_scores` in `vibemon/backend/app/providers/biome/provider.py`.
2. Edit `vibemon/backend/app/providers/biome/const.py` (`WORLD_COVER_PROFILES` weights, `SOLAR_PHASE_BONUS`, `URBAN_*`, `HIGH_ELEVATION_*`).
3. Remove moves from `vibemon/backend/app/providers/biome/data/moves.json` (15 per dropped type).
4. If `solar_phase` removed from payload: stop persisting it in `BiomePayload` / `fetch`; ensure `BirthSeed.solar_phase` still available to other providers.
5. Update `tests/providers/test_biome_provider.py` and element identity tests (e.g. river-near-forest cases).
6. Optionally slim Overpass query if Water trimmed (unlikely).

### Music

1. Update `MusicProvider.exposed_elements` and `determine_element_scores` in `vibemon/backend/app/providers/music/provider.py`.
2. Edit `classify_genre.json`, `classify_mood.json`, and optionally remove `classify_instrument.json` usage.
3. Remove move entries from `vibemon/backend/app/providers/music/data/moves.json` (15 per dropped type); run provider-balance-analysis / move-generator quotas.
4. If valence/key/instrument layers removed: simplify `Track` schema and ReccoBeats field includes in `ensure_full_track`.
5. If tagging should use all resolved tracks: score from `TrackInfo` before ReccoBeats filter (or persist tags on failed-audio rows).
6. Update `tests/app/providers/music/test_provider.py`, `test_classify.py`, and fixture payloads.

### All providers

1. Define **multi-provider birth** compositor (union vs max per type) **before** wide trims.
2. Rebalance compositor so dropped types can still appear from sibling providers when linked.
3. Align `exposed_elements` blurbs with scoring — e.g. Ghost must not cite “historical footprint” if built-up does not score Ghost.
4. Consider **re-homing** deleted move flavor to adjacent types (e.g. alpine dragon moves → Rock) vs retiring learnsets for single-provider births.

---

## Code references

| Area | Path |
| --- | --- |
| Climate scoring + WMO | `vibemon/backend/app/providers/climate/provider.py` |
| Climate moves | `vibemon/backend/app/providers/climate/data/moves.json` |
| Biome scoring + tables | `vibemon/backend/app/providers/biome/provider.py`, `const.py` |
| Biome moves | `vibemon/backend/app/providers/biome/data/moves.json` |
| Biome raster / water | `biome/raster/worldcover/`, `biome/raster/elevation/`, `biome/water/overpass/` |
| Music scoring | `vibemon/backend/app/providers/music/provider.py` |
| Music classify rules | `vibemon/backend/app/providers/music/data/classify_{genre,mood,instrument}.json` |
| Music utils | `vibemon/backend/app/providers/music/utils.py` |
| Music moves | `vibemon/backend/app/providers/music/data/moves.json` |
| Tests | `tests/providers/test_climate_provider.py`, `test_biome_provider.py`, `tests/app/providers/music/` |

---

## Open questions

- Should multi-provider synthesis **union** element rankings or take **max per type** across providers?
- If climate/biome drop Fairy/Dark/Ghost/Psychic, do we **re-home** move flavor under adjacent types or accept learnset loss for single-provider births?
- Is **Dragon** worth 15 moves × N providers for rare signals, or a **compositor-only capstone** (dual-type when two providers agree)?
- Should **`solar_phase`** become its own micro-provider or part of a **celestial** provider instead of biome’s payload?
- After biome Psychic trim, does dawn stillness need **any** terrain proxy, or is music + timestamp enough?
- Should music element scoring use **all MusicBrainz-resolved tracks** while base stats stay ReccoBeats-only?
- Cut **valence/key nudges** entirely, or only when genre rules already matched the label?
- Are **Bug / Ice / Flying / Poison** worth 15 moves each on music, or should metaphor types become compositor-only (rare dual-type when another provider agrees)?
- When climate and music both score **Dragon**, should the compositor **suppress** the weaker signal or allow stacked mythic typing?
