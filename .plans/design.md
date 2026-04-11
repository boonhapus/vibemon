# Vibemon
### Design Document

---

## Table of Contents

1. [Vision](#1-vision)
2. [System Architecture](#2-system-architecture)
3. [Data Source Provider System](#3-data-source-provider-system)
4. [The Generation Pipeline](#4-the-generation-pipeline)
5. [Stat System](#5-stat-system)
6. [Visual Generation](#6-visual-generation)
7. [Battle System](#7-battle-system)
8. [API Reference](#8-api-reference)
9. [Data Models](#9-data-models)
10. [Frontend Architecture](#10-frontend-architecture)
11. [Error Handling & Fallbacks](#11-error-handling--fallbacks)
12. [Technology Stack](#12-technology-stack)
13. [Build Phases](#13-build-phases)

---

## 1. Vision

Vibemon is a browser-based monster-battling game where your creature is generated from your real-world digital life. Connect Spotify and GitHub, share your location, and a unique Vibemon is created whose stats, appearance, and elemental type are a direct reflection of how you actually spend your time — your listening habits, your coding patterns, the weather outside your window.

You then battle a procedurally generated enemy: a "creature of the moment" born from the current datetime and local weather. Two players in the same city at the same hour face the same enemy.

### Design Principles

**Determinism.** Given the same inputs at the same moment, generation is fully deterministic — the same snapshot of listening history, commits, and weather always produces the same Vibemon. Drift is intentional: as a user's habits evolve, so does their creature. This is a feature, not instability.

**Expressiveness.** Every stat and visual choice has a traceable origin. A player should be able to look at their monster and understand why it is the way it is. The `VibemonPayload` carries a `stat_origins` map so this can be surfaced in a post-battle breakdown screen.

**Extensibility.** Data sources are first-class plugins. Adding a new source — Strava, Steam, anything — requires one new file and zero changes to the core engine.

**Graceful degradation.** If any external API fails, generation falls back silently to datetime and weather without breaking the experience.

### Scope

The current version covers a single-player battle against a procedurally generated opponent. There is no persistent collection, no multiplayer, and no capture mechanic. The battle system is client-side only.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Browser (SvelteKit SPA)                    │
│                                                                 │
│  ┌────────────────┐    ┌──────────────────────────────────────┐ │
│  │  Auth Screen   │    │           Battle Screen              │ │
│  │                │    │  ┌──────────────┐ ┌──────────────┐   │ │
│  │ - Spotify      │    │  │Player Vibemon│ │Enemy Vibemon │   │ │
│  │ - GitHub       │    │  │ (Blob SVG)   │ │ (Blob SVG)   │   │ │
│  │ - Location     │    │  └──────────────┘ └──────────────┘   │ │
│  └───────┬────────┘    │      Battle Store (battle.ts)        │ │
│          │             └──────────────────────────────────────┘ │
│          │ POST /api/v1/generate                                │
└──────────┼──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Python Backend (Litestar)                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      Orchestrator                         │  │
│  │  1. Build GenerationContext from request                  │  │
│  │  2. Dispatch active providers concurrently                │  │
│  │  3. Merge SourceData objects                              │  │
│  │  4. Normalise stats                                       │  │
│  │  5. Generate VisualDNA                                    │  │
│  │  6. Generate moves                                        │  │
│  │  7. Return player + enemy VibemonPayloads                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐  │
│  │  Spotify    │  │   GitHub    │  │  Weather / Datetime    │  │
│  │  Provider   │  │   Provider  │  │  Provider              │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬────────────┘  │
└─────────┼────────────────┼────────────────────┼────────────────┘
          │                │                    │
          ▼                ▼                    ▼
    Spotify API       GitHub API          Open-Meteo API
    MusicBrainz API                       (free, no key)
    Last.fm API
    (key in env vars)
```

The backend is stateless per-request. There is no session management and no database. The frontend holds the generated Vibemon payload in memory for the duration of a battle session.

---

## 3. Data Source Provider System

Every data source is an independent Python class implementing the `VibemonProvider` abstract base. The orchestrator knows nothing about individual sources — it only calls `fetch()` and receives a `SourceData` object. This is the entire contract.

### The Provider Interface

```python
from abc import ABC, abstractmethod
from attrs import define, field
from typing import Optional
from datetime import datetime


@define
class SourceData:
    """
    Normalised output from any data provider.
    All stat factors are floats in [0.0, 1.0].
    The orchestrator merges multiple SourceData objects by averaging
    non-None values across providers.
    """
    hp_factor:         Optional[float] = None  # activity volume / endurance
    attack_factor:     Optional[float] = None  # intensity / aggression
    defense_factor:    Optional[float] = None  # consistency / stability
    sp_attack_factor:  Optional[float] = None  # creativity / variety
    sp_defense_factor: Optional[float] = None  # depth / focus
    speed_factor:      Optional[float] = None  # tempo / cadence

    # Providers vote for element(s) with a confidence weight in [0.0, 1.0].
    # The orchestrator resolves the final element by summing votes.
    element_votes: list[tuple[str, float]] = field(factory=list)

    # Visual hints used to seed the colour palette
    hue_primary:   Optional[float] = None  # 0.0–360.0 (HSL)
    hue_secondary: Optional[float] = None
    luminosity:    Optional[float] = None  # 0.0–1.0

    # Displayed in the battle UI as flavour text
    flavour_text: Optional[str] = None

    raw: dict = field(factory=dict)


@define
class GenerationContext:
    """All input the orchestrator passes to every provider."""
    user_id:     str
    timestamp:   datetime
    latitude:    Optional[float]
    longitude:   Optional[float]
    auth_tokens: dict[str, str]  # {"spotify": "Bearer ...", "github": "ghp_..."}


class VibemonProvider(ABC):
    """
    Abstract base for all Vibemon data sources.

    Each provider is responsible for fetching and normalising its own
    data independently. Providers never call other providers. Network
    errors are caught internally; a provider returns whatever partial
    data it could collect, or raises ProviderUnavailableError if nothing
    could be retrieved.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier, e.g. 'spotify', 'github'."""
        ...

    @abstractmethod
    async def fetch(self, context: GenerationContext) -> SourceData:
        ...
```

### Registering a New Provider

```python
# providers/__init__.py
from .spotify import SpotifyProvider
from .github  import GitHubProvider
from .weather import WeatherProvider

PROVIDER_REGISTRY: list[type[VibemonProvider]] = [
    SpotifyProvider,
    GitHubProvider,
    WeatherProvider,
]
```

`WeatherProvider` is always active. All other providers activate when their `auth_token` is present in the request. Adding a new source means creating one file and appending one line here.

---

## 4. The Generation Pipeline

### Player Vibemon

```
POST /api/v1/generate
  │
  ├── Build GenerationContext from request body
  │
  ├── Determine active providers
  │   (any provider whose token is present; WeatherProvider always runs)
  │
  ├── asyncio.gather(*[p.fetch(ctx) for p in active_providers], return_exceptions=True)
  │   ├── each item: SourceData → include in merge; BaseException → skip (silent failure)
  │   └── (happy path) Spotify / GitHub / Weather → SourceData A, B, C
  │
  ├── merge_source_data([A, B, C])
  ├── compute_stats(merged, seed)
  ├── generate_visual_dna(merged, stats, seed)
  ├── generate_moves(stats, seed)
  │
  └── Return VibemonPayload
```

### Merging Source Data

When multiple providers contribute, scalar factors are averaged across all providers that returned a non-`None` value for that field. Elements are resolved by summing vote weights across all providers.

```python
def merge_source_data(sources: list[SourceData]) -> SourceData:
    merged = SourceData()

    scalar_fields = [
        "hp_factor", "attack_factor", "defense_factor",
        "sp_attack_factor", "sp_defense_factor", "speed_factor",
        "hue_primary", "hue_secondary", "luminosity",
    ]
    for field in scalar_fields:
        values = [getattr(s, field) for s in sources if getattr(s, field) is not None]
        if values:
            setattr(merged, field, sum(values) / len(values))

    vote_totals: dict[str, float] = {}
    for s in sources:
        for element, weight in s.element_votes:
            vote_totals[element] = vote_totals.get(element, 0.0) + weight
    merged.element_votes = sorted(vote_totals.items(), key=lambda x: -x[1])

    merged.flavour_text = " | ".join(
        s.flavour_text for s in sources if s.flavour_text
    )
    return merged
```

### Enemy Vibemon

The enemy is generated from `WeatherProvider` only. Its seed is derived from a rounded location and hour bucket, so two players in the same city during the same hour always face the same opponent.

```python
async def generate_enemy(context: GenerationContext) -> VibemonPayload:
    enemy_context = GenerationContext(
        user_id=(
            f"enemy_{context.timestamp.strftime('%Y%m%d%H')}"
            f"_{round(context.latitude, 1)}_{round(context.longitude, 1)}"
        ),
        timestamp=context.timestamp,
        latitude=context.latitude,
        longitude=context.longitude,
        auth_tokens={},
    )
    source_data = await WeatherProvider().fetch(enemy_context)
    return build_vibemon(enemy_context, source_data)
```

### The Deterministic Seed

```python
import uuid

def make_seed(user_id: str, source_id: str) -> int:
    """
    UUID5 produces a stable integer from any (user, source) pair.
    Using a namespaced hash avoids the string-concatenation collision
    risk of a naive approach (e.g. 'ab'+'cde' == 'abc'+'de').
    """
    namespace = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    return int(uuid.uuid5(namespace, f"{user_id}:{source_id}").hex, 16)
```

---

## 5. Stat System

Vibemon stats mirror Generation I Pokémon: six integers, each in `[1, 255]`.

| Stat | Meaning |
|---|---|
| `hp` | Endurance; volume of activity |
| `attack` | Raw intensity; aggression |
| `defense` | Consistency; stability; resistance |
| `sp_attack` | Creativity; variety; range |
| `sp_defense` | Depth; focus; mindfulness |
| `speed` | Tempo; cadence; reactiveness |

### Normalisation

Each `SourceData` factor (a float in `[0.0, 1.0]`) is mapped to an integer stat. A small seeded variance is applied so two monsters with identical factors are still subtly different.

```python
MIN_STAT = 30
MAX_STAT = 230

def factor_to_stat(factor: float, rng: random.Random) -> int:
    base = MIN_STAT + factor * (MAX_STAT - MIN_STAT)
    variance = rng.uniform(-0.10, 0.10) * base
    return max(1, min(255, round(base + variance)))
```

Missing factors default to `0.5`.

### Elements

The element with the highest total vote weight from all providers becomes the primary type. If the runner-up holds at least 50% of the winner's weight, it is assigned as a secondary type.

| Element | Hue | Saturation |
|---|---|---|
| Fire | 20° | 0.85 |
| Water | 210° | 0.80 |
| Ice | 190° | 0.65 |
| Electric | 55° | 0.90 |
| Grass | 115° | 0.75 |
| Ground | 32° | 0.30 |
| Dark | 275° | 0.25 |
| Psychic | 315° | 0.80 |
| Normal | 35° | 0.20 |

### Provider Mappings

### Enemy BST Scaling

The player's Vibemon reflects multiple weeks of personal data across up to three providers; the enemy is weather-only. To prevent the gap from making battles feel trivial, the enemy's stats are scaled after generation so its Base Stat Total (BST) falls within ±15% of the player's BST. The enemy's stat *distribution* — which stats are high vs. low — remains authentic to the weather data; only the total magnitude is adjusted.

```python
def scale_enemy_stats(player_stats: VibemonStats, enemy_stats: VibemonStats) -> VibemonStats:
    player_bst = sum([
        player_stats.hp, player_stats.attack, player_stats.defense,
        player_stats.sp_attack, player_stats.sp_defense, player_stats.speed,
    ])
    enemy_bst = sum([
        enemy_stats.hp, enemy_stats.attack, enemy_stats.defense,
        enemy_stats.sp_attack, enemy_stats.sp_defense, enemy_stats.speed,
    ])

    lower = player_bst * 0.85
    upper = player_bst * 1.15

    if lower <= enemy_bst <= upper:
        return enemy_stats  # already within band; no adjustment needed

    target_bst = max(lower, min(upper, enemy_bst))
    scale = target_bst / enemy_bst

    def adj(v: int) -> int:
        return max(1, min(255, round(v * scale)))

    return VibemonStats(
        hp=adj(enemy_stats.hp),
        attack=adj(enemy_stats.attack),
        defense=adj(enemy_stats.defense),
        sp_attack=adj(enemy_stats.sp_attack),
        sp_defense=adj(enemy_stats.sp_defense),
        speed=adj(enemy_stats.speed),
        element=enemy_stats.element,
        element_secondary=enemy_stats.element_secondary,
    )
```

This scaling is applied in `generate_enemy()` after `build_vibemon()` returns, before the enemy `VibemonPayload` is included in the response.

### Provider Mappings


**SpotifyProvider**

Spotify deprecated their Audio Features API in November 2024. All acoustic feature data comes from MusicBrainz and Last.fm enrichment. Spotify itself provides track history, artist metadata, and album information.

| Feature | Stat / Vote |
|---|---|
| BPM (normalised 60–180 bpm → 0–1) | `speed_factor` |
| BPM < 80 | `defense_factor` ↑ |
| Unique genre count (normalised 1–10) | `sp_attack_factor` |
| Genre: metal / punk / hardcore | `attack_factor` ↑ |
| Genre: classical / ambient / folk | `sp_defense_factor` ↑ |
| Track count in 7-day window (norm. 1–50) | `hp_factor` |
| Mood tag: dark / melancholy | `Dark` vote (0.6) |
| Mood tag: energetic / upbeat | `Electric` vote (0.7) |
| Mood tag: chill / acoustic | `Water` vote (0.5) |
| Mood tag: aggressive / intense | `Fire` vote (0.6) |
| Mood/energy hue (see below) | `hue_primary` |
| Average listening hour 22h–4h | `Dark` vote (+0.4 bonus) |

**GitHubProvider**

| Feature | Stat / Vote |
|---|---|
| Commit count, 30 days (norm. 0–200) | `hp_factor` |
| Repository count (norm. 1–30) | `sp_attack_factor` |
| Primary language: C / Rust / Assembly | `defense_factor` ↑ |
| Primary language: Python / JS / Ruby | `speed_factor` ↑ |
| PR merge rate (merged / opened) | `sp_defense_factor` |
| Issue close rate (closed / opened) | `speed_factor` ↑ |
| Average commit hour 22h–4h | `Dark` vote (0.5) |
| Average commit hour 6h–10h | `Electric` vote (0.4) |

**WeatherProvider**

| Feature | Stat / Vote |
|---|---|
| Temp < 5°C | `Ice` vote (0.9) |
| Temp 5–14°C | `Water` vote (0.7) |
| Temp 15–24°C | `Grass` vote (0.5) |
| Temp 25–34°C | `Fire` vote (0.7) |
| Temp ≥ 35°C | `Ground` vote (0.9) |
| Wind speed (norm. 0–80 km/h) | `speed_factor` |
| Precipitation > 5mm | `defense_factor` ↑ |
| Clear sky, high UV | `attack_factor` ↑ |
| Humidity (norm. 0–100%) | `hp_factor` |
| Hour 0–5h | `Dark` vote (0.6) |
| Temperature cold→hot (190°→10°) | `hue_primary` (linear interpolation) |

### Hue Derivation from Energy and Valence

`hue_primary` is derived from two normalised signals aggregated across the user's recent tracks: **energy** (0–1, from BPM and genre intensity tags) and **valence** (0–1, from mood tags such as "upbeat", "melancholy", "chill"). This is culturally neutral and changes with actual listening mood.

```python
def derive_hue(energy: float, valence: float) -> float:
    """
    Maps (energy, valence) to a hue in [0, 360).

    High energy + high valence → warm yellows/oranges (40–60°)
    High energy + low valence  → aggressive reds (0–20°)
    Low energy  + high valence → bright greens/cyans (100–180°)
    Low energy  + low valence  → cool blues/purples (220–280°)
    """
    base_hue   = 220 + valence * 140    # low-valence=220° (blue), high=360°/0° (red) wraps
    energy_shift = (energy - 0.5) * -80 # high energy pulls toward warm end
    return (base_hue + energy_shift) % 360
```

`energy` is computed as the average of normalised BPM and the proportion of energetic/aggressive genre tags in the track window. `valence` is derived from the ratio of positive mood tags ("upbeat", "happy", "euphoric") to negative ones ("melancholy", "dark", "sad") in the same window.

---

## 6. Visual Generation

Vibemons are rendered entirely in code — no hand-drawn assets. The frontend generates a unique creature silhouette using a seeded spline-blob algorithm. Stats drive shape complexity, limb style, eye expression, and colour. The result is deterministic: the same `VisualDNA` always produces the same creature.

### VisualDNA

The backend computes a `VisualDNA` object from the merged `SourceData` and final stats. The frontend uses it as its sole input for rendering.

```python
@define
class VisualDNA:
    # Blob geometry
    n_points:        int    # hull control points: 8–12
    spikiness:       float  # radius variance: 0.0 (round) – 0.6 (jagged)
    limb_count:      int    # 0, 1, or 2
    limb_style:      str    # "stubby" | "elongated" | "wing"
    eye_count:       int    # 1 (cyclops) or 2
    eye_size:        float  # fraction of body radius: 0.04–0.12
    eye_shape:       str    # "circle" | "slit" | "diamond" | "compound"
    mouth_style:     str    # "none" | "line" | "open" | "fanged"
    texture_pattern: str    # "none" | "dots" | "stripes" | "scales" | "cracks"

    # Colour palette (HSL tuples: hue 0–360, saturation 0–1, lightness 0–1)
    color_primary:   tuple[float, float, float]
    color_secondary: tuple[float, float, float]
    color_accent:    tuple[float, float, float]
    color_eye:       tuple[float, float, float]

    # Personality modifiers applied at render time
    outline_weight:  float  # 0.5–3.5
    glow_intensity:  float  # 0.0–1.0
    size_scale:      float  # 0.8–1.3
    animation_speed: float  # 0.5–2.0 seconds
```

### Stat → Visual Parameter Mapping

| Parameter | Driving Stat | Formula |
|---|---|---|
| `n_points` | Speed | `8 + floor(speed / 255 × 4)` |
| `spikiness` | Attack | `0.1 + (attack / 255) × 0.5` |
| `limb_count` | HP | < 85 → 0; 85–170 → 1; > 170 → 2 |
| `limb_style` | Speed vs. Defense | speed > defense → "wing" / "elongated"; else "stubby" |
| `eye_count` | Sp. Attack | > 170 → 1 (cyclops); else 2 |
| `eye_size` | Sp. Defense | `0.04 + (sp_defense / 255) × 0.08` |
| `eye_shape` | Element | See table below |
| `mouth_style` | Attack | < 85 → "none"; < 170 → "line"; < 220 → "open"; ≥ 220 → "fanged" |
| `texture_pattern` | Defense | < 85 → "none"; < 140 → "dots"; < 190 → "stripes"; < 220 → "scales"; ≥ 220 → "cracks" |
| `outline_weight` | Defense | `0.5 + (defense / 255) × 3.0` |
| `glow_intensity` | Sp. Attack | `sp_attack / 255` |
| `size_scale` | HP | `0.8 + (hp / 255) × 0.5` |
| `animation_speed` | Speed | `0.5 + (speed / 255) × 1.5` |

**Eye shape by element:**

| Fire | Water | Ice | Electric | Grass | Ground | Dark | Psychic | Normal |
|---|---|---|---|---|---|---|---|---|
| diamond | circle | slit | compound | circle | slit | slit | diamond | circle |

### Colour Generation

```python
ELEMENT_BASE_HUES = {
    "Fire": 20, "Water": 210, "Ice": 190, "Electric": 55,
    "Grass": 115, "Ground": 32, "Dark": 275, "Psychic": 315, "Normal": 35,
}

def generate_palette(
    merged: SourceData,
    stats: VibemonStats,
    rng: random.Random,
) -> tuple:
    base_hue = merged.hue_primary or ELEMENT_BASE_HUES[stats.element]
    base_hue = (base_hue + rng.uniform(-15, 15)) % 360

    # More Sp. Attack → more vivid
    sat = 0.50 + (stats.sp_attack / 255) * 0.40
    lum = merged.luminosity or 0.55

    h_secondary = (base_hue + 30  + rng.uniform(-10, 10)) % 360  # analogous
    h_accent    = (base_hue + 180 + rng.uniform(-20, 20)) % 360  # near-complementary

    return (
        (base_hue,    sat,                    lum),
        (h_secondary, sat * 0.85,             lum * 1.05),
        (h_accent,    min(sat * 1.2, 1.0),    lum * 0.90),
        (h_accent,    0.90,                   0.70),         # eyes always pop
    )
```

### Frontend Blob Renderer

The renderer runs entirely in TypeScript / SVG inside `VibemonRenderer.svelte`. It takes a `VisualDNA` prop and a numeric seed, and produces a fully self-contained SVG. All rendering steps are deterministic.

#### Step 1 — Generate Hull Points

```typescript
function generateHullPoints(dna: VisualDNA, seed: number): Point[] {
  const rng = seededRandom(seed);  // Mulberry32
  const BASE_RADIUS = 75;          // px, within a 200×220 viewBox centred at (100, 110)
  const points: Point[] = [];

  for (let i = 0; i < dna.nPoints; i++) {
    const baseAngle   = (2 * Math.PI * i) / dna.nPoints;
    const angleJitter = (rng() - 0.5) * (Math.PI / dna.nPoints) * 0.6;
    const angle       = baseAngle + angleJitter;
    const radius      = BASE_RADIUS * (1 - dna.spikiness / 2 + rng() * dna.spikiness);
    points.push({
      x: 100 + Math.cos(angle) * radius,
      y: 110 + Math.sin(angle) * radius,
    });
  }
  return points;
}
```

#### Step 2 — Smooth the Hull

Converts the control points into a smooth closed path using Catmull-Rom → Cubic Bézier conversion.

```typescript
function smoothClosedPath(pts: Point[]): string {
  const n  = pts.length;
  const p  = (i: number) => pts[(i + n) % n];
  let path = `M ${p(0).x} ${p(0).y}`;

  for (let i = 0; i < n; i++) {
    const [p0, p1, p2, p3] = [p(i - 1), p(i), p(i + 1), p(i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    path += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return path + ' Z';
}
```

#### Step 3 — Limbs

For each limb, select a hull point in the lower-lateral region and extrude a secondary shape outward. Limb style:

- `"stubby"` — small sub-blob at 60% parent radius
- `"elongated"` — tapered ellipse extending 1.5× body radius outward
- `"wing"` — mirrored curved path pair with reduced opacity

#### Step 4 — Eyes and Mouth

Eyes anchor to the centroid of the topmost 20% of hull points. Two eyes are offset by `±eye_size × radius`; a cyclops eye is centred. Mouth anchors to the bottom-centre of the hull. Both are scaled SVG path templates.

#### Step 5 — Texture

A `<pattern>` element is applied over the body path at 15–25% opacity, allowing the primary colour to show through.

#### Step 6 — Final Assembly

```svelte
<!-- VibemonRenderer.svelte -->
<script lang="ts">
  import type { VisualDNA } from '$lib/types';
  import { seededRandom } from '$lib/utils/rng';

  export let dna:     VisualDNA;
  export let seed:    number;
  export let uid:     string;
  export let flipped: boolean = false;

  const hsl = ([h, s, l]: [number, number, number]) =>
    `hsl(${h.toFixed(1)}, ${(s * 100).toFixed(1)}%, ${(l * 100).toFixed(1)}%)`;

  $: hullPoints  = generateHullPoints(dna, seed);
  $: bodyPath    = smoothClosedPath(hullPoints);
</script>

<svg
  viewBox="0 0 200 220"
  style="
    --cp: {hsl(dna.colorPrimary)};
    --cs: {hsl(dna.colorSecondary)};
    --ca: {hsl(dna.colorAccent)};
    --ce: {hsl(dna.colorEye)};
    --ow: {dna.outlineWeight}px;
    transform: scaleX({flipped ? -1 : 1}) scale({dna.sizeScale});
    animation: float {dna.animationSpeed}s ease-in-out infinite alternate;
  "
>
  <defs>
    <filter id="glow-{uid}">
      <feGaussianBlur stdDeviation="{dna.glowIntensity * 6}" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Limbs render behind body -->
  <!-- Body -->
  <path
    d={bodyPath}
    fill="var(--cp)"
    stroke="var(--cs)"
    stroke-width="var(--ow)"
    filter="url(#glow-{uid})"
  />
  <!-- Texture overlay, eyes, mouth -->
</svg>
```

---

## 7. Battle System

The battle system is entirely client-side. All state lives in a Svelte store. There is no server validation.

### Moves

Each Vibemon has exactly four moves, selected deterministically from its element's pool based on its stat profile. The signature move is always included.

**Move pools — 8 moves per element (3 physical · 3 special · 2 status)**

**FIRE**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Ember Slash | Physical | 40 | 100 | — |
| Sear Strike | Physical | 65 | 95 | — |
| Blaze Crash | Physical | 90 | 85 | — |
| Scorch Pulse | Special | 45 | 100 | — |
| Combustion | Special | 75 | 90 | — |
| **Inferno** ★ | Special | 110 | 75 | — |
| Heat Veil | Status | — | — | Own Sp. Atk +1 |
| Cinder Shroud | Status | — | — | Enemy Defense −1 |

**WATER**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Surge Slam | Physical | 40 | 100 | — |
| Riptide Bash | Physical | 65 | 95 | — |
| Torrent Rush | Physical | 90 | 85 | — |
| Drench Pulse | Special | 45 | 100 | — |
| Cascade | Special | 75 | 90 | — |
| **Deluge** ★ | Special | 110 | 75 | — |
| Mist Veil | Status | — | — | Own Sp. Def +1 |
| Soak | Status | — | — | Enemy Sp. Atk −1 |

**ICE**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Frost Strike | Physical | 40 | 100 | — |
| Crystal Bash | Physical | 65 | 90 | — |
| Shatter Crash | Physical | 90 | 85 | — |
| Chill Pulse | Special | 45 | 100 | — |
| Glaciate | Special | 75 | 90 | — |
| **Blizzard** ★ | Special | 110 | 70 | — |
| Ice Veil | Status | — | — | Own Defense +1 |
| Freeze Shroud | Status | — | — | Enemy Speed −1 |

**ELECTRIC**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Spark Strike | Physical | 40 | 100 | — |
| Volt Slam | Physical | 65 | 95 | — |
| Thunder Crash | Physical | 90 | 80 | — |
| Shock Pulse | Special | 45 | 100 | — |
| Discharge | Special | 75 | 90 | — |
| **Thunderstrike** ★ | Special | 110 | 75 | — |
| Static Field | Status | — | — | Enemy Speed −1 |
| Charge | Status | — | — | Own Attack +1 |

**GRASS**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Vine Lash | Physical | 40 | 100 | — |
| Bramble Slam | Physical | 65 | 90 | — |
| Root Crash | Physical | 90 | 85 | — |
| Spore Pulse | Special | 45 | 100 | — |
| Bloom Burst | Special | 75 | 90 | — |
| **Overgrowth** ★ | Special | 110 | 75 | — |
| Seed Drain | Status | — | — | ⅛ enemy max HP drained per turn |
| Tangle | Status | — | — | Enemy Speed −1 |

**GROUND**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Quake Strike | Physical | 40 | 100 | — |
| Boulder Slam | Physical | 65 | 95 | — |
| **Landslide** ★ | Physical | 90 | 85 | — |
| Tremor Pulse | Special | 45 | 100 | — |
| Dust Surge | Special | 65 | 90 | — |
| Tectonic | Special | 100 | 75 | — |
| Sand Veil | Status | — | — | Own Defense +1 |
| Burrow | Status | — | — | Next hit against self has 50% miss chance |

**DARK**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Shadow Strike | Physical | 40 | 100 | — |
| Hex Slash | Physical | 65 | 95 | — |
| Dread Crash | Physical | 90 | 85 | — |
| Curse Pulse | Special | 45 | 100 | — |
| Nightfall | Special | 75 | 90 | — |
| **Void** ★ | Special | 110 | 70 | — |
| Drain | Status | — | — | Heals 25% of damage dealt this turn |
| Phantom Shroud | Status | — | — | Enemy Sp. Atk −1 |

**PSYCHIC**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Phase Strike | Physical | 40 | 100 | — |
| Echo Bash | Physical | 65 | 90 | — |
| Warp Crash | Physical | 90 | 85 | — |
| Mind Pulse | Special | 45 | 100 | — |
| Distortion | Special | 75 | 90 | — |
| **Mindbreak** ★ | Special | 110 | 75 | — |
| Foresee | Status | — | — | Own Speed +1 |
| Unravel | Status | — | — | Enemy Defense −1 |

**NORMAL**

| Name | Category | Power | Accuracy | Effect |
|---|---|---|---|---|
| Strike | Physical | 40 | 100 | — |
| Bash | Physical | 65 | 100 | — |
| **Pummel** ★ | Physical | 90 | 95 | — |
| Force Pulse | Special | 45 | 100 | — |
| Rush Surge | Special | 65 | 95 | — |
| Overwhelm | Special | 100 | 85 | — |
| Fortify | Status | — | — | Own Defense +1 |
| Lunge | Status | — | — | Own Speed +1 |

### Move Selection

```python
def generate_moves(stats: VibemonStats, seed: int) -> list[Move]:
    rng       = random.Random(seed)
    pool      = MOVE_POOL[stats.element]
    signature = next(m for m in pool if m.is_signature)
    candidates = [m for m in pool if not m.is_signature]

    def weight(m: Move) -> float:
        w = 1.0
        if m.category == "physical": w *= stats.attack    / 128
        if m.category == "special":  w *= stats.sp_attack / 128
        if m.category == "status":   w *= stats.sp_defense / 128
        return max(w, 0.1)

    physicals = [m for m in candidates if m.category == "physical"]
    specials  = [m for m in candidates if m.category == "special"]

    # Guarantee at least one physical and one special move.
    guaranteed = [
        rng.choices(physicals, weights=[weight(m) for m in physicals], k=1)[0],
        rng.choices(specials,  weights=[weight(m) for m in specials],  k=1)[0],
    ]
    seen = {m.name for m in guaranteed}

    # Fill the third slot from the remaining candidate pool (any category).
    remaining = [m for m in candidates if m.name not in seen]
    third = rng.choices(remaining, weights=[weight(m) for m in remaining], k=1)[0]

    return [signature] + guaranteed + [third]
```

### Damage Formula

Adapted from Generation I:

```
Damage = floor(((2 × 50 / 5 + 2) × Power × A/D) / 50 + 2) × Modifier

A        = Attacker's Attack (physical) or Sp. Attack (special)
D        = Defender's Defense (physical) or Sp. Defense (special)
Modifier = STAB × TypeEffectiveness × Random(0.85, 1.00)
STAB     = 1.5 if move type matches attacker's element, else 1.0
```

Stat stages modify A and D:

| Stage | ×0.25 | ×0.33 | ×0.50 | ×1.00 | ×1.50 | ×2.00 | ×2.50 |
|---|---|---|---|---|---|---|---|
| | −6 | −4 | −2 | 0 | +2 | +4 | +6 |

### Type Effectiveness

| Attacking ↓ / Defending → | Fire | Water | Ice | Elec | Grass | Ground | Dark | Psychic | Normal |
|---|---|---|---|---|---|---|---|---|---|
| **Fire** | ×0.5 | ×0.5 | ×2 | ×1 | ×2 | ×1 | ×1 | ×1 | ×1 |
| **Water** | ×2 | ×0.5 | ×1 | ×1 | ×0.5 | ×2 | ×1 | ×1 | ×1 |
| **Ice** | ×0.5 | ×0.5 | ×0.5 | ×1 | ×2 | ×2 | ×1 | ×1 | ×1 |
| **Electric** | ×1 | ×2 | ×1 | ×0.5 | ×0.5 | ×0 | ×1 | ×1 | ×1 |
| **Grass** | ×0.5 | ×2 | ×1 | ×1 | ×0.5 | ×2 | ×1 | ×1 | ×1 |
| **Ground** | ×2 | ×1 | ×1 | ×0 | ×0.5 | ×1 | ×1 | ×1 | ×1 |
| **Dark** | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×0.5 | ×2 | ×1 |
| **Psychic** | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×2 | ×0.5 | ×1 |
| **Normal** | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 | ×1 |

`×0` = immune.

### Battle State

```typescript
// src/lib/stores/battle.ts

type Phase = 'player-turn' | 'enemy-turn' | 'animating' | 'victory' | 'defeat';

type BattleMon = {
  vibemon:      Vibemon;
  currentHp:    number;
  maxHp:        number;
  statStages:   Record<'attack' | 'defense' | 'spAttack' | 'spDefense' | 'speed', number>;
  statusEffect: 'drain' | 'seed' | 'burrowed' | null;
};

type BattleState = {
  phase:  Phase;
  player: BattleMon;
  enemy:  BattleMon;
  log:    string[];
  turn:   number;
};
```

### Turn Flow

```
Player selects a move
  │
  ├── Compare Speed (with stat stage modifiers); ties broken by RNG
  │
  ├── Faster attacker executes move:
  │   ├── Accuracy roll → Math.random() * 100 < move.accuracy
  │   ├── On hit: calculate damage, apply to target HP
  │   ├── Apply move effect (stat stage, drain, seed, burrow)
  │   ├── Trigger hit animation
  │   └── Check KO → if so, resolve victory/defeat
  │
  └── Slower attacker executes move (if still alive):
      └── Same flow
```

### Enemy AI

```typescript
function chooseEnemyMove(state: BattleState): Move {
  const { enemy, player } = state;
  const available = enemy.vibemon.moves;
  const playerHpRatio = player.currentHp / player.maxHp;
  const enemyHpRatio  = enemy.currentHp  / enemy.maxHp;

  return weightedChoice(available, available.map(m => {
    let w = 1.0;
    if (playerHpRatio < 0.25 && m.power > 80) w *= 3.0;
    if (enemyHpRatio  < 0.50 && m.category === 'status') w *= 1.5;
    if (m.category === 'physical') w *= enemy.vibemon.stats.attack    / 128;
    if (m.category === 'special')  w *= enemy.vibemon.stats.spAttack  / 128;
    return w;
  }));
}
```

---

## 8. API Reference

All routes are prefixed `/api/v1`.

### `POST /generate`

Generates both the player's Vibemon and the enemy Vibemon in a single request.

**Request body:**
```json
{
  "user_id":   "spotify:abc123",
  "latitude":  51.5074,
  "longitude": -0.1278,
  "auth_tokens": {
    "spotify": "Bearer eyJ...",
    "github":  "ghp_..."
  }
}
```

**Response `200 OK`:**
```json
{
  "player": { "uid": "...", "name": "Pyrox", "source": "spotify+weather", "stats": {}, "moves": [], "visual_dna": {}, "flavour_text": "..." },
  "enemy":  { "..." }
}
```

**`422 Unprocessable Entity`** — location is missing and no city name fallback was provided.

**`200 OK` with `"fallback": true`** — all providers failed; response contains a valid payload generated from datetime only.

### `GET /auth/github/callback`

Proxies GitHub's OAuth token exchange to avoid exposing the client secret in the browser.

### `GET /health`

```json
{
  "status": "ok",
  "providers": {
    "spotify":      "reachable",
    "github":       "reachable",
    "weather":      "reachable",
    "musicbrainz":  "reachable",
    "lastfm":       "reachable"
  }
}
```

---

## 9. Data Models

```python
from attrs import define
from typing import Optional


@define
class VibemonStats:
    hp:                int
    attack:            int
    defense:           int
    sp_attack:         int
    sp_defense:        int
    speed:             int
    element:           str
    element_secondary: Optional[str] = None


@define
class Move:
    name:         str
    type:         str
    category:     str   # "physical" | "special" | "status"
    power:        int   # 0 for status moves
    accuracy:     int   # 0–100
    is_signature: bool = False
    effect:       Optional[str] = None


@define
class VisualDNA:
    n_points:        int
    spikiness:       float
    limb_count:      int
    limb_style:      str
    eye_count:       int
    eye_size:        float
    eye_shape:       str
    mouth_style:     str
    texture_pattern: str
    color_primary:   tuple[float, float, float]
    color_secondary: tuple[float, float, float]
    color_accent:    tuple[float, float, float]
    color_eye:       tuple[float, float, float]
    outline_weight:  float
    glow_intensity:  float
    size_scale:      float
    animation_speed: float


@define
class VibemonPayload:
    uid:          str
    name:         str
    source:       str
    stats:        VibemonStats
    moves:        list[Move]
    visual_dna:   VisualDNA
    flavour_text: str
    stat_origins: dict[str, str]  # e.g. {"speed": "BPM avg 142 from your top tracks"}
    fallback:     bool = False
```

### Name Generation

Names are 2–3 syllable portmanteaus drawn from a per-element syllable bank, seeded by the Vibemon's RNG. Each bank contains ~40 syllables, producing names like "Pyrox", "Embrath", "Glacyn", "Voidrel".

```python
SYLLABLES: dict[str, list[str]] = {
    "Fire":     ["pyr", "emb", "bla", "sol", "ign", "kar", "tor", "vul", "cin", "scor", ...],
    "Water":    ["aqu", "tid", "rip", "del", "vas", "mer", "flu", "tur", "bri", "cor", ...],
    "Ice":      ["gla", "fro", "cry", "chi", "sno", "bor", "gel", "arc", "hal", "nim", ...],
    "Electric": ["vol", "sho", "zap", "amp", "thr", "kin", "cra", "sul", "ion", "nex", ...],
    "Grass":    ["vir", "blo", "spr", "flo", "lea", "mos", "tho", "cha", "fer", "gro", ...],
    "Ground":   ["ter", "bou", "qua", "sed", "gra", "mol", "cla", "dus", "bru", "erd", ...],
    "Dark":     ["nox", "sha", "voi", "hex", "dre", "cur", "obs", "phe", "sco", "nul", ...],
    "Psychic":  ["psi", "pha", "tel", "mne", "eso", "var", "mis", "eid", "zer", "kal", ...],
    "Normal":   ["nor", "com", "bas", "sim", "ord", "gen", "pri", "pla", "ven", "mid", ...],
}
```

---

## 10. Frontend Architecture

### Stack

SvelteKit with `adapter-static` — a pure SPA with no server-side rendering. Two routes cover the entire application.

```
src/
├── routes/
│   ├── +page.svelte          # Auth / landing
│   └── battle/
│       └── +page.svelte      # Battle
├── lib/
│   ├── components/
│   │   ├── VibemonRenderer.svelte
│   │   ├── HpBar.svelte
│   │   └── MoveButton.svelte
│   ├── stores/
│   │   └── battle.ts
│   ├── utils/
│   │   ├── rng.ts            # Mulberry32 seeded RNG
│   │   ├── damage.ts         # Damage formula
│   │   └── blobRenderer.ts   # Hull generation, path smoothing
│   └── types.ts
```

### Auth Screen (`/`)

- Spotify OAuth2 PKCE flow — no backend involvement; safe for a pure SPA.
- GitHub OAuth2 — requires backend token exchange via `GET /api/v1/auth/github/callback` to keep the client secret off the browser.
- "Play as Guest" — skips all auth; weather-only Vibemon for both player and enemy.
- Browser Geolocation API. On denial, a city-name text input is shown; the backend geocodes it via Open-Meteo's geocoding endpoint.
- On submit: `POST /api/v1/generate` → store payload → navigate to `/battle`.

### Battle Screen (`/battle`)

```
┌──────────────────────────────────────────────────────┐
│  EMBER-FLAX   [Fire · Dark]              Lv. 50      │
│  ████████████████░░░░   142 / 180 HP                 │
│                                                      │
│                     [Enemy Blob SVG]                 │
│                                                      │
│  [Player Blob SVG]                                   │
│                                                      │
│  PYROX   [Fire]                          Lv. 50      │
│  ████████████████████   167 / 167 HP                 │
│                                                      │
│  ┌───────────────┐  ┌───────────────┐               │
│  │ ★ Inferno     │  │  Sear Strike  │               │
│  │ Special · 110 │  │ Physical · 65 │               │
│  └───────────────┘  └───────────────┘               │
│  ┌───────────────┐  ┌───────────────┐               │
│  │  Heat Veil    │  │ Cinder Shroud │               │
│  │    Status     │  │    Status     │               │
│  └───────────────┘  └───────────────┘               │
│                                                      │
│  ▸ Pyrox used Inferno! It's super effective!         │
│    Ember-Flax took 94 damage.                        │
└──────────────────────────────────────────────────────┘
```

### Animations

| Event | Implementation |
|---|---|
| HP loss | `tweened` store, `cubicOut` easing, 600ms |
| Hit received | CSS `@keyframes shake` on SVG wrapper, 300ms |
| Critical hit | White flash overlay on SVG, 150ms |
| Fainting | `translateY(30px)` + `opacity: 0`, 800ms |
| Move button press | Svelte `spring` store, scale 0.95 → 1.0 |
| Idle float | CSS `@keyframes float` (±6px), period = `animation_speed` seconds |
| Glow pulse | CSS `@keyframes` on SVG filter `stdDeviation`, period = `animation_speed × 1.5`s |
| Victory | Player blob scales up via spring; CSS particle burst |

---

## 11. Error Handling & Fallbacks

### Provider Failure Hierarchy

| Scenario | Behaviour |
|---|---|
| Spotify API unreachable | Skip Spotify; proceed with remaining providers |
| MusicBrainz unreachable | Fall back to Last.fm tag inference only |
| Last.fm unreachable | Spotify contributes track count and country hue only |
| GitHub API unreachable | Skip GitHub; proceed with remaining providers |
| All enrichment providers fail | WeatherProvider alone generates the Vibemon |
| Weather API unreachable | Datetime-only generation (see below) |
| All providers fail | Datetime-only; response is `200` with `"fallback": true` |
| Location denied, no city entered | Backend returns `422`; frontend prompts for city name |
| City geocoding fails | Regional defaults derived from the request's `Accept-Language` header |

### Datetime-Only Generation

When all external APIs are unavailable, a Vibemon is generated from the UTC timestamp alone. Seasonal element assignment accounts for hemisphere using the latitude from `GenerationContext` (negative latitude = Southern Hemisphere, seasons inverted).

```python
def datetime_only_source(timestamp: datetime, latitude: Optional[float] = None) -> SourceData:
    hour  = timestamp.hour
    month = timestamp.month
    dow   = timestamp.weekday()  # 0 = Monday

    # Invert season for Southern Hemisphere
    southern = (latitude is not None) and (latitude < 0)
    adjusted_month = ((month - 1 + 6) % 12) + 1 if southern else month

    speed_factor  = math.sin(math.pi * hour / 23)
    attack_factor = 0.4 if dow >= 5 else 0.3 + (dow / 4) * 0.6

    season_elements = [
        ((12, 1, 2),   "Ice"),
        ((3, 4, 5),    "Grass"),
        ((6, 7, 8),    "Fire"),
        ((9, 10, 11),  "Water"),
    ]
    element = next(e for months, e in season_elements if adjusted_month in months)

    return SourceData(
        speed_factor=speed_factor,
        attack_factor=attack_factor,
        element_votes=[(element, 1.0)],
        flavour_text=f"Born from the {timestamp.strftime('%A')} silence",
    )
```

### Last.fm API Key

Stored as `LASTFM_API_KEY` in backend environment variables. Never exposed to the browser. In local development it lives in `.env` (gitignored); in production it is set as a platform secret.

---

## 12. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend framework | **Litestar 2.x** | ASGI, native async, first-class `attrs` support |
| HTTP client | **Niquests** | Async, HTTP/2, drop-in Requests replacement |
| Data modelling | **attrs + cattrs** | Strict typing, fast serialisation |
| Logging | **structlog** | Structured JSON logs; essential for debugging concurrent provider calls |
| Weather | **Open-Meteo** | Free, no API key, global coverage |
| Music enrichment | **MusicBrainz API** | BPM and genre tags (Spotify audio features deprecated Nov 2024) |
| Music enrichment fallback | **Last.fm API** | Mood and genre inference; single backend environment key |
| Frontend | **SvelteKit 2.x** | Reactive UI, built-in `tweened` / `spring`, minimal bundle |
| Deployment | **adapter-static** | Pure SPA; no Node server required |
| Python packages | **uv** | Speed |
| Node packages | **pnpm** | Speed |

There is no database. The backend is fully stateless.

---

## 13. Build Phases

### Phase 1 — Core Pipeline

Stand up the full generation stack using weather data only. The goal is a complete round-trip: browser sends location → backend returns a valid `VibemonPayload` with all fields populated.

- Litestar app scaffold with `POST /api/v1/generate` and `GET /api/v1/health`
- `GenerationContext`, `SourceData`, and `VibemonProvider` ABC
- `WeatherProvider` implementation (Open-Meteo)
- `make_seed` (UUID5), `factor_to_stat`, stat normalisation
- `VisualDNA` generation — all blob parameters and colour palette
- Syllable name generator (weather element only to start)
- SvelteKit skeleton: location form → `POST /generate` → log JSON response

**Exit criteria:** A weather-only `VibemonPayload` with all fields populated is returned and logged in the browser.

---

### Phase 2 — Spotify Integration

Connect listening history to the generation pipeline. The player's Vibemon should now visibly reflect their music taste.

- Spotify PKCE OAuth flow on the frontend
- `SpotifyProvider`: recent tracks, artist metadata
- MusicBrainz BPM and genre tag lookup (per-track, with in-memory request cache)
- Last.fm tag inference as fallback
- Country → hue lookup
- Multi-provider `merge_source_data` logic active
- Syllable banks completed for all 9 elements

**Exit criteria:** A Spotify-authenticated user receives a Vibemon with stat origins traceable to their listening data, visibly different from the weather-only baseline.

---

### Phase 3 — Visual Rendering

Vibemons become visible creatures on screen.

- `seededRandom` utility (Mulberry32)
- `blobRenderer.ts`: hull generation, Catmull-Rom path smoothing, limb extrusion, eye and mouth placement, texture overlay
- `VibemonRenderer.svelte`: full pipeline assembled, colour CSS variables applied
- Idle float animation driven by `animation_speed`
- Glow filter driven by `glow_intensity`
- Enemy blob rendered with `flipped={true}`

**Exit criteria:** Two visually distinct, animated blob creatures are rendered side-by-side on screen.

---

### Phase 4 — Battle System

A complete, playable battle loop from start to finish.

- Move generation (`generate_moves`) for all 9 elements
- `battle.ts` Svelte store with the full phase state machine
- Damage formula, stat stage modifiers, and type effectiveness
- Enemy AI (weighted random)
- HP bar `tweened` animations
- Hit shake, critical flash, and faint animations
- Victory and defeat screens
- Battle log

**Exit criteria:** A full battle plays out with correct damage calculation, type effectiveness messaging, stat stage changes, and win/loss detection.

---

### Phase 5 — GitHub Integration and Polish

Add the second data source and bring the project to a production-quality state.

- `GET /api/v1/auth/github/callback` OAuth proxy endpoint
- `GitHubProvider`: commits, repos, language breakdown
- GitHub stat mapping active and merged with other providers
- "Play as Guest" mode (weather-only for both player and enemy)
- Flavour text displayed in the battle UI
- Error and loading states throughout
- Mobile-responsive layout
- Auth screen visual design

---

### Phase 6 — Stretch Goals

- **PvP via shared seed URL** — two players share a link; their Vibemons fight with a deterministic battle RNG derived from the URL seed
- **Local collection** — `localStorage`-backed Pokédex of encountered Vibemons
- **Post-battle share card** — `canvas` → PNG export
- **Additional providers** — Strava (activity data), Steam (playtime and genre)
