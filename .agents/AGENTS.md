# AGENTS.md — Vibemon

Vibemon is a browser-based monster-battling game. Connect Spotify and GitHub, share your location, and a unique creature is generated whose stats, appearance, and element reflect your real digital life. You then battle a procedurally generated enemy derived from the current time and local weather.

No database. The backend is fully stateless per-request.

**Python:** use **3.12 or newer** project-wide (asyncio `TaskGroup`, `asyncio.timeout`, `except*` / exception groups).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | **Svelte 5** + **SvelteKit 2** (`adapter-static`, pure SPA) |
| Backend | **Python 3.12+** + **Litestar 2.x** (ASGI, stateless) |
| HTTP client | **Niquests** (async, HTTP/2) |
| Data modelling | **attrs** + **cattrs** |
| Logging | **structlog** |
| Package managers | **pnpm** (Node), **uv** (Python) |
| External APIs | Spotify, GitHub, Open-Meteo (free, no key), MusicBrainz, Last.fm |

---

## Frontend: Svelte 5 Rules

Use **Svelte 5 syntax exclusively**. LLMs default to Svelte 4 — do not.

- Reactive state: `$state()`, `$derived()`, `$effect()` — never `let` reactive declarations
- Props: `$props()` — never `export let`
- Snippets replace slots
- Animations: `Tween` and `Spring` from `svelte/motion` (Svelte 5 rune-based API)
- State stores: use `$state`-backed classes or objects — not `writable`/`readable`
- Init: `npx sv create`

---

## Project Structure

```
frontend/
  src/
    routes/
      +page.svelte              # Auth screen (Spotify PKCE, GitHub OAuth, location)
      battle/+page.svelte       # Battle screen
    lib/
      components/
        VibemonRenderer.svelte  # VisualDNA + seed → deterministic SVG blob
      stores/
        battle.ts               # Battle state machine (phases, HP, log, turns)
      utils/
        blobRenderer.ts         # Hull generation, path smoothing, limbs, eyes, texture
        seededRandom.ts         # Mulberry32 PRNG

backend/
  app/
    providers/
      registry.py               # PROVIDER_REGISTRY
      base.py                   # VibemonProvider ABC, SourceData, GenerationContext
      spotify.py
      github.py
      weather.py
    engine/
      stats.py                  # factor_to_stat, compute_stats, merge_source_data
      visual.py                 # generate_visual_dna
      moves.py                  # generate_moves
      names.py                  # syllable name generator
    routes/
      generate.py               # POST /api/v1/generate
      auth.py                   # GET /api/v1/auth/github/callback
```

---

## API Endpoints

```
POST /api/v1/generate               → GenerateRequest → GenerateResponse
GET  /api/v1/health
GET  /api/v1/auth/github/callback   (GitHub OAuth proxy)
```

---

## Generation Pipeline

`POST /api/v1/generate` runs these steps in order:

```
1. Build GenerationContext from request body
2. Activate providers — WeatherProvider always runs; others activate when their token is present
3. asyncio.gather(*[p.fetch(ctx) for p in active_providers], return_exceptions=True)
   → treat each result: BaseException → skip that provider; SourceData → include in merge
4. merge_source_data(results)       — average scalar factors; sum element votes
5. compute_stats(merged, seed)      — factor_to_stat with ±10% seeded variance
6. generate_visual_dna(merged, stats, seed)
7. generate_moves(stats, seed)
8. generate_enemy(context)          — WeatherProvider only; BST-scaled to ±15% of player BST
9. Return GenerateResponse(player=VibemonPayload, enemy=VibemonPayload)
```

---

## Core Data Models

Canonical shapes match [.plans/design.md](../.plans/design.md) §9 and task specs. JSON uses **snake_case** keys aligned with Python field names.

```python
@define
class GenerationContext:
    user_id:     str
    timestamp:   datetime
    latitude:    Optional[float]
    longitude:   Optional[float]
    auth_tokens: dict[str, str]    # {"spotify": "Bearer ...", "github": "ghp_..."}

@define
class SourceData:
    # All factors are floats in [0.0, 1.0]; None means this provider didn't contribute
    hp_factor:         Optional[float] = None
    attack_factor:     Optional[float] = None
    defense_factor:    Optional[float] = None
    sp_attack_factor:  Optional[float] = None
    sp_defense_factor: Optional[float] = None
    speed_factor:      Optional[float] = None
    element_votes:     list[tuple[str, float]] = field(factory=list)  # [("Fire", 0.7)]
    hue_primary:       Optional[float] = None  # HSL hue 0–360
    hue_secondary:     Optional[float] = None
    luminosity:        Optional[float] = None  # 0–1
    flavour_text:      Optional[str]   = None
    raw:               dict            = field(factory=dict)

@define
class VibemonStats:
    hp:                int              # all stats 1–255
    attack:            int
    defense:           int
    sp_attack:         int
    sp_defense:        int
    speed:             int
    element:           str
    element_secondary: Optional[str] = None

@define
class VisualDNA:
    # Geometry
    n_points:        int    # 8–12
    spikiness:       float  # 0.0–0.6
    limb_count:      int    # 0, 1, or 2
    limb_style:      str    # "stubby" | "elongated" | "wing"
    eye_count:       int    # 1 or 2
    eye_size:        float  # 0.04–0.12
    eye_shape:       str    # "circle" | "slit" | "diamond" | "compound"
    mouth_style:     str    # "none" | "line" | "open" | "fanged"
    texture_pattern: str    # "none" | "dots" | "stripes" | "scales" | "cracks"
    # Colour (HSL tuples)
    color_primary:   tuple[float, float, float]
    color_secondary: tuple[float, float, float]
    color_accent:    tuple[float, float, float]
    color_eye:       tuple[float, float, float]
    # Personality
    outline_weight:  float  # 0.5–3.5
    glow_intensity:  float  # 0.0–1.0
    size_scale:      float  # 0.8–1.3
    animation_speed: float  # 0.5–2.0s

@define
class Move:
    name:          str
    type:          str       # elemental type, e.g. "Fire" (matches battle STAB rules)
    category:      str       # "physical" | "special" | "status"
    power:         int       # 0 for status moves
    accuracy:      int       # 0–100
    is_signature:  bool = False
    effect:        Optional[str] = None

@define
class VibemonPayload:
    uid:           str
    name:          str
    source:        str      # e.g. "merged" | "weather" for traceability
    stats:         VibemonStats
    moves:         list[Move]
    visual_dna:    VisualDNA
    flavour_text:  str
    stat_origins:  dict[str, str]
    fallback:      bool = False
```

Deterministic generation for a given request uses `make_seed(user_id, "vibemon")` for the merged player creature (and the same pattern for the enemy `user_id`). Move pools and battle logic treat `Move.type` as the move’s elemental type.

---

## Provider Interface

```python
class VibemonProvider(ABC):
    @property
    @abstractmethod
    def source_id(self) -> str: ...      # e.g. "spotify", "github", "weather"

    @abstractmethod
    async def fetch(self, context: GenerationContext) -> SourceData: ...
```

Register in `providers/registry.py`:

```python
PROVIDER_REGISTRY: list[type[VibemonProvider]] = [
    SpotifyProvider,
    GitHubProvider,
    WeatherProvider,
]
```

Adding a new data source = one new file + one line here.

> **Spotify note:** The Spotify Audio Features API was deprecated November 2024. BPM and acoustic data come from **MusicBrainz** (primary) and **Last.fm** (fallback). Never call the `audio-features` endpoint.

---

## Elements

`Fire · Water · Ice · Electric · Grass · Ground · Dark · Psychic · Normal`

- **Primary** = highest total vote weight across all providers
- **Secondary** = runner-up only if its weight ≥ 50% of the winner's weight

---

## Stat Normalisation

```python
MIN_STAT, MAX_STAT = 30, 230

def factor_to_stat(factor: float, rng: random.Random) -> int:
    base = MIN_STAT + factor * (MAX_STAT - MIN_STAT)
    variance = rng.uniform(-0.10, 0.10) * base
    return max(1, min(255, round(base + variance)))
```

Missing `SourceData` factors default to `0.5`. Merging averages all non-`None` values across providers.

---

## Deterministic Seed

```python
def make_seed(user_id: str, source_id: str) -> int:
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    return int(uuid.uuid5(namespace, f"{user_id}:{source_id}").hex, 16)
```

Enemy `user_id`: `f"enemy_{timestamp:%Y%m%d%H}_{round(lat,1)}_{round(lon,1)}"` — ensures two players in the same city during the same hour face the same opponent.

---

## Enemy BST Scaling

The enemy is weather-only; the player may have up to three providers. After enemy generation, scale its Base Stat Total to within ±15% of the player's BST. Preserve the stat *distribution* — adjust magnitude only.

---

## Error Handling

Provider failures are silent — generation continues with whatever providers succeed. The generation pipeline uses **`asyncio.gather(..., return_exceptions=True)`** (step 3) so one provider’s exception does not cancel the others; each outcome is either a **`SourceData`** or an error to skip.

| Failure | Behaviour |
|---|---|
| Any single provider fails | Skip it; continue with the rest |
| All enrichment providers fail | WeatherProvider alone generates the Vibemon |
| WeatherProvider also fails | Datetime-only fallback (seasonal element from UTC + hemisphere) |
| Any fallback path taken | HTTP 200 with `fallback: true` in payload |
| Location denied, no city provided | HTTP 422; frontend prompts for city name |

---

## Environment Variables

```
# Backend only — never expose to the browser
LASTFM_API_KEY
GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET

# Frontend — safe to expose (PKCE flow, no secret needed)
PUBLIC_SPOTIFY_CLIENT_ID
```
