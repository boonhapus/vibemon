# Fitness Provider

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | High |
| **Area** | Providers |
| **Related** | — |

## Summary

A **Vibemon** is born from the trainer's body — sleep, activity, recovery, and vitals in the weeks before birth. Multiple wearables and health platforms merge into one **Affinity** for physiological state.

## Problem

Single-API providers cover one slice of life (music, film, code). Physiological state spans many platforms with overlapping metrics (HRV from Whoop and Oura, steps from Fitbit and Google Fit). Trainers need one **Fitness** toggle, not eight separate providers.

## Concept

The first **multi-source** provider: discover available adapters from **TrainerSecrets**, fetch partial observations concurrently, merge by configurable priority or democratic mean, and emit a unified **FitnessObservation**. Frontend shows a single "Fitness" entry; source configuration lives in the secrets layer.

## Design

### Data sources (field-mergeable)

| Platform | Coverage | Secrets Required |
|----------|----------|------------------|
| Whoop | Recovery, Sleep, HRV, RHR, Strain, Activity | `fitness.whoop.token` |
| Oura | Sleep, HRV, RHR, Readiness, Temperature, Activity | `fitness.oura.token` |
| Eight Sleep | Sleep stages, HRV, RHR, Bed temperature, Latency | `fitness.eight_sleep.token` |
| Apple Health | Steps, Exercise, Heart rate, Sleep (inferred), Workouts | `fitness.apple_health.jwt` |
| Google Fit | Steps, Calories, Heart rate, Sleep (inferred), Workouts | `fitness.google_fit.refresh_token` |
| Fitbit | Steps, Sleep, HRV, RHR, Active minutes | `fitness.fitbit.token` |
| Strava | Runs, Rides, Swims, Heart rate, Elevation, Pace | `fitness.strava.access_token` |
| Garmin | Steps, Sleep, HRV, RHR, Body Battery, Intensity minutes | `fitness.garmin.email` + `fitness.garmin.password` |

### Secrets

| Key | Required | Purpose |
| --- | -------- | ------- |
| `fitness.config` | no | Per-subschema source priority (JSON, see below) |
| `fitness.<platform>.*` | see table | Platform credentials — one or more |

**`fitness.config` schema**

```json
{
  "activity_sources": ["google_fit", "strava", "fitbit"],
  "sleep_sources": ["eight_sleep", "oura", "whoop"],
  "recovery_sources": ["whoop"],
  "body_sources": ["oura", "eight_sleep"],
  "window_days": 60
}
```

If absent, defaults to democratic merge across all available adapters.

### Intermediate schema

Every adapter produces a partial `FitnessObservation`. All fields optional — unpopulated means "this source doesn't supply this dimension."

```python
class ActivityMetrics(FrozenSchema):
    avg_daily_steps: int | None = None
    active_calories_avg_kcal: float | None = None
    exercise_minutes_avg: float | None = None
    workout_types: tuple[str, ...] = ()
    workout_days_per_week: float | None = None
    elevation_gain_avg_m: float | None = None      # Strava-heavy users
    distance_avg_km: float | None = None

class SleepMetrics(FrozenSchema):
    avg_duration_hours: float | None = None
    deep_pct: float | None = None
    rem_pct: float | None = None
    latency_minutes: float | None = None
    consistency_score: float | None = None          # 0-1 bed/wake regularity
    temperature_celsius: float | None = None

class RecoveryMetrics(FrozenSchema):
    hrv_ms_avg: float | None = None                # RMSSD
    resting_hr_bpm: float | None = None
    respiratory_rate_bpm: float | None = None
    readiness_score: float | None = None

class BodyMetrics(FrozenSchema):
    temperature_celsius_avg: float | None = None    # core/skin trend
    weight_kg: float | None = None

class FitnessObservation(FrozenSchema):
    activity: ActivityMetrics = ActivityMetrics()
    sleep: SleepMetrics = SleepMetrics()
    recovery: RecoveryMetrics = RecoveryMetrics()
    body: BodyMetrics = BodyMetrics()
    source: str                                      # adapter identifier
```

### Merge protocol

`fetch()` follows these steps:

1. **Discover** — Scan `TrainerSecrets` for known `fitness.<platform>.*` keys
2. **Filter** — If `fitness.config` exists, exclude adapters not listed in any `*_sources` array
3. **Fetch** — Call each active adapter concurrently via `asyncio.gather`
4. **Merge** — For each subschema (`activity`, `sleep`, `recovery`, `body`):
   - If config has a priority list for that subschema: scan sources in order, take **first non-None** field value
   - If no config: take **mean across non-None values** for numeric fields, union for tuple fields, first non-None for string fields
5. **Annotate** — Attach **Provider Note** per missing subschema (e.g. `"Sleep data unavailable"`), per excluded adapter (`"Whoop steps excluded by config — only recovery used"`)

```python
async def fetch(self, seed, *, secrets) -> dict:
    adapters = discover_adapters(secrets)
    config = load_config(secrets)
    adapters = filter_adapters(adapters, config)
    partials = await asyncio.gather(*[a.fetch(seed, secrets) for a in adapters])
    merged = FitnessMerger.merge(partials, config)
    return merged.model_dump()
```

### Type mapping

| Type | Signal |
|------|--------|
| NORMAL | Balanced activity, no extreme in any dimension |
| FIRE | High-intensity workouts, HIIT, sprinting, elevated HR |
| WATER | Swimming, low HRV, high sleep consistency |
| GRASS | Hiking, outdoor walking, low stress, nature proximity |
| ICE | Very cold exposure, low temperature, winter sports |
| FLYING | High weekly distance, varied movement types |
| FIGHTING | Martial arts, combat sports, high strain score |
| POISON | Very low HRV, poor sleep, high resting HR (stressed) |
| GROUND | Walking, steady-state cardio, low elevation change |
| BUG | Many short activities, high step count, restless |
| ROCK | Heavy lifting, strength training, slow-twitch |
| GHOST | Very low activity, poor sleep consistency, late bed |
| DRAGON | Endurance sports, triathlon, extreme output |
| ELECTRIC | High HRV, fast cadence, responsive cardiovascular |
| DARK | Late-night activity, erratic sleep, high latency |
| STEEL | Heavy strength, low body temp, consistent routine |
| FAIRY | Dance, bodyweight, low strain, high REM, positive readiness |
| PSYCHIC | Yoga, meditation, low RHR, high HRV, deliberate movement |

### Signal design (6 stat axes)

| Stat | Signal | Source |
|------|--------|--------|
| HP | Sleep duration + consistency | `SleepMetrics.avg_duration_hours`, `.consistency_score` |
| Attack | Strain intensity | `RecoveryMetrics.readiness_score` (inverted — go hard when ready) × `ActivityMetrics.exercise_minutes_avg` |
| Defense | Recovery baseline | `RecoveryMetrics.hrv_ms_avg`, `.resting_hr_bpm` |
| Sp. Attack | Activity variety | `.workout_types` breadth × `.workout_days_per_week` |
| Sp. Defense | Temperature stability | `BodyMetrics.temperature_celsius_avg` variance (low variance → high stability) |
| Speed | Recent step cadence | `ActivityMetrics.avg_daily_steps` / 24h |

Missing source → neutral contribution to affected stat + **Provider Note**.

### Intensity

Average of normalized `RecoveryMetrics.readiness_score` and inverse of `BodyMetrics.temperature_celsius_avg` deviation from baseline. High readiness + stable temp = charged and available. Low readiness + feverish = drained.

### Provider notes

| Condition | Note |
| --------- | ---- |
| No adapters connected | `"No fitness data sources configured"` |
| Merged but missing an entire subschema | `"Sleep data unavailable — consider connecting Eight Sleep or Oura"` |
| Config filtered out a connected source | `"Whoop steps excluded by fitness.config, only recovery used"` |
| Conflicting HRV from two sources | `"HRV differs between sources (Whoop: 52ms, Eight Sleep: 48ms) — using priority config"` |
| Window <14d | `"Short window — signals may be noisy"` |

### Moves

Fitness-themed move names in `data/moves.json` (e.g. Deep Breath, Cold Plunge, Active Recovery, Peak Zone, Sleep Debt, PR, Cool Down, Heart Rate Spike).

### Proposed structure

```
providers/fitness/
  __init__.py              # re-export FitnessProvider
  provider.py              # FitnessProvider(VibeProvider)
  schema.py                # FitnessObservation + subschemas
  merge.py                 # FitnessMerger — priority-list + democratic merge
  const.py                 # Activity → VibemonTypeT mapping
  data/
    moves.json
  adapters/
    __init__.py            # discover_adapters(), adapter registry
    _protocol.py           # FitnessAdapter protocol (fetch → FitnessObservation)
    whoop.py
    oura.py
    eight_sleep.py
    apple_health.py
    google_fit.py
    fitbit.py
    strava.py
    garmin.py
```

**Adapter protocol (`_protocol.py`)**

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class FitnessAdapter(Protocol):
    source: str  # e.g. "whoop"

    async def fetch(self, *, seed: BirthSeed,
                    secrets: TrainerSecrets) -> FitnessObservation:
        ...
```

Each adapter is a standalone file. Registration is a dict in `adapters/__init__.py`:

```python
_ADAPTERS: dict[str, type[FitnessAdapter]] = {
    "whoop": WhoopAdapter,
    "oura": OuraAdapter,
    "eight_sleep": EightSleepAdapter,
    ...
}

def discover_adapters(secrets: TrainerSecrets) -> list[FitnessAdapter]:
    return [
        cls() for key, cls in _ADAPTERS.items()
        if any(secrets.get(f"fitness.{key}.{field}") for field in _REQUIRED_FIELDS[key])
    ]
```

### Wiring

Same opt-in pattern — gated behind secrets, registered in `scripts/_common.py` and `frontend/src/lib/domains/generation/provider-options.ts`. Frontend toggle shows as a single "Fitness" entry; source configuration happens in the secrets layer.

## Open Questions

- Which two adapters ship first for MVP (Whoop + Oura vs. Strava + Fitbit)?
- Garmin email/password auth acceptable vs. OAuth-only policy?
- Minimum `window_days` before **Provider Warning** for noisy signals?
