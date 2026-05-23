# Spotify / Sound Provider Plan

## Goal

Add a `VibeProvider` that derives a Vibemon's `Affinity` from the **soundtrack of birth** — the trainer's actual Spotify listening data at `seed.timestamp`. Sits alongside `ClimateProvider` and the planned `GeographyProvider` as a peer, opt-in per birth.

## Why a separate provider

- Climate signals are *atmospheric* (sky). Geography signals are *physical place* (ground). Sound signals are *cultural/personal* (taste).
- Two trainers at the same coordinate and second listening to wildly different music should produce wildly different creatures. Neither climate nor geography can express that.
- Spotify's genre vocabulary maps cleanly onto element flavor; ReccoBeats' rebuilt audio analysis gives clean energy/tempo/valence numbers that map cleanly onto stats.
- Keeps single-source-of-truth per provider for replay and rate limiting.

## Scope

- In scope:
  - New `app/providers/sound/` package mirroring `app/providers/climate/`.
  - One concrete `SoundProvider(VibeProvider)`.
  - Two thin async clients: `SpotifyAPIClient` and `ReccoBeatsAPIClient`, both `niquests.AsyncSession` subclasses with `LoggingHook` + `RateLimiterHook`.
  - `data/genre_anchors.json` (hand-curated flavor source of truth) and `data/genre_families.json` (script-generated lookup table).
  - `data/moves.json` of sound-flavored moves (15 per element × 18 elements = 270), authored via `.agents/skills/vibemon/move-generator`.
  - One-off bootstrap script `vibemon/backend/scripts/build_sound_genre_families.py`.
  - Settings additions: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`.
  - Tests under `vibemon/backend/tests/app/providers/sound/`.
- Out of scope (this plan):
  - **OAuth / Trainer-Spotify linking infrastructure.** Captured in a separate plan: `docs/development/plans/trainer-spotify-linking-plan.md`. This plan declares `trainer.spotify_refresh_token` as a precondition.
  - **`BirthSeed.trainer_id` addition.** Captured in `docs/development/adr/0001-birth-seed-gains-trainer-id.md`.
  - **Provider-picker UX** (the trainer-facing surface for selecting providers per birth) — separate work.
  - Any reliance on the **2024-deprecated** Spotify endpoints (see "Deprecation Wall").
  - Last.fm, ListenBrainz, MusicBrainz at runtime (MB is used by the bootstrap script only — see below — and only optionally).
  - Caching layer (defer until measured).

## The Deprecation Wall

Spotify removed access for new apps to a broad set of endpoints in November 2024. Plan **must not depend** on these.

| Endpoint | Status | v1 use |
|---|---|---|
| `GET /audio-features/{id}` | **dead** for new apps | none — fields sourced from ReccoBeats |
| `GET /audio-analysis/{id}` | **dead** | none |
| `GET /recommendations` | **dead** | none |
| `GET /artists/{id}/related-artists` | **dead** | none |
| `GET /browse/featured-playlists` | **dead** | none |
| `GET /browse/categories` and category playlists | **dead** | none |
| `GET /recommendations/available-genre-seeds` | **dead** | none — genre vocab sourced from Every Noise at Once |
| 30-second preview URLs on track objects | **dead** (null) | none |
| `GET /me/top/tracks?time_range=short_term` | **alive** | core listening fingerprint |
| `GET /me/player/recently-played` | **alive** | blended into stat computation, drives intensity z-score |
| `GET /tracks/{id}` (name, explicit, release date, duration, ISRC) | **alive** | track metadata |
| `GET /artists/{id}` (name, genres) | **alive** | genre → element scoring |

**Consequence**: the canonical audio-features stat mapping (energy/danceability/valence/tempo/etc.) is unrecoverable from Spotify itself. ReccoBeats provides a community-rebuilt equivalent keyed by ISRC and Spotify track ID, MIT-licensed, free. Coverage is partial (~70-90% for typical catalogs) — fallback policy below.

## Locked Decisions

1. **Sound is a peer provider, per-birth trainer opt-in.** Not auto-enabled; trainer explicitly selects sound as one of the providers for a given birth. If sound is not selected, it does not run; the BirthSeed simply doesn't include it.
2. **Personal mode only — no market mode.** Sound requires a linked Spotify account. A trainer without `trainer.spotify_refresh_token` cannot opt sound into a birth (precondition fails at birth-request validation, before `BirthSeed` is constructed).
3. **`name = "sound"`**, persisted in `Affinity.provider_id`. Package directory is `sound/` (not `spotify/`) — leaves room for ListenBrainz / Apple Music / Last.fm folding in under the same provider later without a rename.
4. **Replay determinism for dev tuning, not historical fidelity.** `fetch()` reduces upstream payloads to only the fields `synthesize()` consumes. The reduced payload is what `BirthSnapshot` persists. Re-running `synthesize()` against the captured snapshot remains the dev-tuning surface; reconstructing the original Spotify state is not a goal.
5. **Async like climate.** `niquests.AsyncSession` subclasses. `asyncio.gather` for parallel fetches.
6. **Listening window:** `top_tracks?time_range=short_term` (~4w) as primary, `recently-played` (last 50 items, time-bucketed by day) blended at low weight for "what you were listening to today" influence.
7. **Genre → Element scoring via static dict lookup at runtime.** Dict generated offline by the bootstrap script; runtime does no genre-resolution HTTP.
8. **Stats from ReccoBeats audio analysis** (energy, acousticness, liveness, valence, danceability, tempo) joined to Spotify tracks via ISRC.
9. **Intensity = climate-style z-score** of per-day `sqrt(volume_norm × diversity_norm)` against the listening-window distribution, sigmoid-mapped. No floor.
10. **Payload retention** under Spotify ToS: store only the reduced payload; **never store popularity, follower count, or any other unused Spotify Content fields**. Acknowledged as "loose reading" of ToS — acceptable for pre-launch hobby project; revisit before any public launch.
11. **Move pool: 15 moves per element × 18 elements = 270 total**, authored via `.agents/skills/vibemon/move-generator`. Move IDs prefixed `sound.*`. `universal.tackle` and `universal.breaking_point` reused via base class loader.
12. **ReccoBeats coverage fallback:** tracks not in ReccoBeats contribute **zero** to stat computation; they still contribute to element scoring via their Spotify genres. Bias: stats reflect the well-catalogued slice of listening; elements reflect the full slice.
13. **`rebalance_existing_vibemons` and related code are dev-only tooling.** Banner this clearly in module docstrings and `vibemon/backend/scripts/README.md` so future engineers don't mistake it for a production workflow. Provider balance is tuned **before** release per `VibeProvider`; post-launch rebalancing is fallback, not primary.

## Architecture Overview

```
BirthSeed (gains trainer_id, see ADR-0001)
    │
    ├── trainer opted in to sound?
    │   └── trainer.spotify_refresh_token must exist (precondition)
    │
SoundProvider.fetch(seed)
    │
    ├── SpotifyAPIClient
    │   ├── _ensure_token() ← refresh-token grant
    │   ├── me_top_tracks(short_term)         ┐
    │   ├── me_recently_played()              ├── asyncio.gather
    │   └── artists(unique_artist_ids)        ┘
    │
    ├── ReccoBeatsAPIClient
    │   └── audio_analysis(isrcs OR spotify_track_ids)  (batched, parallel)
    │
    └── reduce → SoundPayload (the snapshot)
            ├── tracks: [(id, isrc, name, explicit, release_date, duration_ms, played_at?)]
            ├── artists: [(id, name, genres[])]
            ├── audio: {isrc: {energy, acousticness, liveness, valence, danceability, tempo}}
            └── window_meta: {day_buckets: {date: track_count}}

SoundProvider.synthesize(seed, payload)
    │
    ├── element scoring (genres → GENRE_FAMILIES dict → element scores)
    │       (categorical bonuses: explicit-majority → DARK, etc.)
    ├── stat signals from ReccoBeats audio means (uncovered tracks dropped)
    ├── intensity = sigmoid(z_score(today_signal, window_signal_distribution))
    └── starter moves via _starter_move_weights + _pick_starter_moves helpers
    │
    └── Affinity(provider_id="sound", ...)
```

## File Layout

```
vibemon/backend/app/providers/sound/
├── __init__.py
├── api.py                  # SpotifyAPIClient, ReccoBeatsAPIClient, token mgr
├── const.py                # GENRE_FAMILIES loaded from data/, tier thresholds
├── provider.py             # SoundProvider(VibeProvider)
└── data/
    ├── genre_anchors.json  # hand-curated flavor source of truth (~10/element)
    ├── genre_families.json # generated by build_sound_genre_families.py
    ├── genre_families.report.md  # diff-friendly stats from last bootstrap run
    └── moves.json          # 270 moves from move-generator skill

vibemon/backend/scripts/
└── build_sound_genre_families.py  # one-off bootstrap script (PEP 723, uv-runnable)
```

## Stat Mapping (locked)

All six stats sourced from **ReccoBeats audio analysis**, averaged across tracks in the listening window (uncovered tracks dropped per decision 12).

| Stat | Signal | Source |
|---|---|---|
| HP | mean track duration (log-scaled) | Spotify (alive) |
| Attack | mean energy | ReccoBeats |
| Defense | mean (acousticness + liveness) / 2 | ReccoBeats |
| Sp. Attack | mean valence | ReccoBeats |
| Sp. Defense | mean danceability | ReccoBeats |
| Speed | mean tempo (BPM, normalized via Signal) | ReccoBeats |

**Why this maps cleanly:**
- Spotify's canonical audio-features mapping was designed for exactly this kind of derivation. ReccoBeats re-implements it free; the thematic fit is preserved.
- Fully orthogonal to climate (temp/wind/elevation/radiation/precipitation/wind) and geography (population/road/building/amenity/green/transport) stat axes.
- Fully orthogonal to the intensity formula's data axis (Spotify listening volume × diversity). The "double-dip" concern from the Spotify-only draft is structurally resolved — stats and intensity now draw from completely separate raw data.

## Element Scoring (genre-driven, flavor-only)

For each artist in the window, look up their genre tags in `GENRE_FAMILIES: dict[str, VibemonTypeT]` (the bootstrap-generated table). Accumulate per-element scores weighted by that artist's track count in the window. Then a small categorical bonus pass:

- `explicit_ratio > 0.5` → `+0.2 DARK`
- `single_genre_lock` (one genre tag accounts for >70% of weighted score) → `+0.2` to that element
- `pure NORMAL fallback` (no genre tags matched anything) → `+0.3 NORMAL` safety net (mirrors climate's NORMAL backstop)

**Why the quality bar on `GENRE_FAMILIES` is relaxed:** under the ReccoBeats stat architecture, the genre table drives *only* element selection — never stats. A misclassified tag affects which elements show up, not the creature's stat block. Bootstrap script can ship a coarser k-NN propagation than originally planned without stat-block consequences.

## Intensity Formula

Following the climate pattern (`app/providers/climate/provider.py:125-162`):

```python
def calculate_intensity(per_day_signals: list[float], *, today_index: int = -1) -> float:
    """
    Per-day signal = sqrt(volume_norm × diversity_norm) for that day.
    volume_norm: log-scaled minutes-listened-that-day mapped to [0,1].
    diversity_norm: log-scaled distinct-artists-that-day mapped to [0,1].

    Intensity = sigmoid of z-score of today's signal against the window distribution.
    """
    if len(per_day_signals) < 2 or not (stdev := statistics.stdev(per_day_signals)):
        return 0.5  # climate-style fallback for thin windows
    z = (per_day_signals[today_index] - statistics.mean(per_day_signals)) / stdev
    return 1.0 / (1.0 + math.exp(-z))
```

**Per-day signal source:** `recently-played` time-bucketed by day. The 50-item cap means window coverage varies per trainer (heavy listener: hours; light listener: weeks). When the window collapses to a single day, intensity falls back to 0.5 (climate uses the same fallback for empty-stdev cases).

**No floor.** Sound is a precondition-gated provider; trainers without listening data can't opt in, so the all-zero case can't reach `Affinity.merge()`.

## Genre-Family Bootstrap (script) vs Runtime Lookup (library)

### Bootstrap (script — dev-time only)

**Location:** `vibemon/backend/scripts/build_sound_genre_families.py`
**Invocation:** `uv run vibemon/backend/scripts/build_sound_genre_families.py` (PEP 723 inline metadata)
**Runs:** ad-hoc — on first build, then quarterly refresh, plus any time the unmatched-tag log shows pressure.

**Responsibilities:**
- Reads anchors from `app/providers/sound/data/genre_anchors.json` (the hand-curated `{element: [canonical_genres]}` source of truth, ~10 per element).
- Fetches Every Noise at Once's full genre dataset (community CSV mirror or scrape; treated as untrusted external input — fail loudly on schema drift).
- Runs k-NN propagation from anchors across Every Noise's similarity space to assign every Spotify genre tag to an element.
- Writes two artifacts, both committed to the repo:
  - `app/providers/sound/data/genre_families.json` — the dict (`tag → element`) consumed at runtime.
  - `app/providers/sound/data/genre_families.report.md` — diff-friendly stats: total tag count, per-element breakdown, orphan list, anchor-distance histogram, top-50 "surprising" assignments for human review.
- Idempotent: same anchors + same Every Noise snapshot → byte-identical output.

**MusicBrainz parent-walk fallback:** **not needed in v1.** Under the relaxed quality bar (genre table is flavor-only), unmatched tags safely contribute zero to element scoring. Add MB later only if the unmatched-tag log shows persistent pressure.

**Allowed dependencies:** anything (HTTP, scrapers, pandas). This is a dev tool, never in the runtime path.

### Runtime (library — per-birth)

**Location:** `vibemon/backend/app/providers/sound/`
**Loads:** `data/genre_families.json` at import time into an immutable `Mapping[str, VibemonTypeT]`.

**Responsibilities:**
- `const.py` exposes `GENRE_FAMILIES`. No HTTP. No I/O at request time beyond the import.
- `provider.py` does plain dict lookup per artist tag during `synthesize()`. Unmatched tags → emit a structured log (`provider="sound", event="genre.unmatched", tag=...`) and contribute zero score.

**Forbidden:** no MusicBrainz, no Every Noise, no Last.fm — no network calls of any kind for genre resolution at runtime. The bootstrap script is the only path data enters the table.

### Maintenance loop

1. Runtime accumulates `genre.unmatched` log events.
2. Dev queries those logs periodically.
3. If a tag shows up at meaningful volume → add to `genre_anchors.json` if it deserves explicit flavor intent, or just re-run the script with refreshed Every Noise data.
4. Commit updated `genre_families.json` + `genre_families.report.md`. The report's diff is the PR's review surface.

## Thin API Clients

Both clients mirror `OpenMeteoAPIClient` shape exactly. Only Spotify diverges (token refresh).

```python
class SpotifyAPIClient(niquests.AsyncSession):
    """
    Fetches listening + catalog data from Spotify Web API.

    Built only against the post-2024-deprecation surface — no audio-features,
    no recommendations, no related-artists.

    Further reading:
      https://developer.spotify.com/documentation/web-api
    """
    provider_name = "spotify.web_api"

    def __init__(self, client_id: str, client_secret: str, **session_opts):
        RATE_LIMITER = RateLimiterHook(
            # Rolling 30s window; documented ceiling ~180 req/min.
            (180, dt.timedelta(minutes=1)),
            provider=SpotifyAPIClient.provider_name,
        )
        RETRY_POLICY = niquests.RetryConfiguration(
            total=5, backoff_factor=2,
            status_forcelist=[429, 500, 502, 503],
            allowed_methods=["GET"], raise_on_status=False,
            respect_retry_after_header=True,
        )
        hooks = cast(Any, LoggingHook(provider=...) + RATE_LIMITER)
        super().__init__(
            base_url="https://api.spotify.com/", hooks=hooks, retries=RETRY_POLICY,
            **session_opts,
        )
        # token state set externally via configure_for_trainer()
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: dt.datetime | None = None

    def configure_for_trainer(self, refresh_token: str) -> None: ...
    async def _ensure_token(self) -> None: ...  # called from pre_request hook
    async def me_top_tracks(self, *, time_range: str = "short_term", limit: int = 50): ...
    async def me_recently_played(self): ...
    async def artists(self, ids: list[str]): ...  # batched, 50 max


class ReccoBeatsAPIClient(niquests.AsyncSession):
    """
    Fetches audio analysis (energy, danceability, valence, tempo, etc.)
    keyed by ISRC or Spotify track ID.

    Community rebuild of Spotify's deprecated audio-features.
    Free, MIT-licensed dataset.

    Further reading:
      https://reccobeats.com
    """
    provider_name = "reccobeats.audio_analysis"

    def __init__(self, **session_opts):
        RATE_LIMITER = RateLimiterHook(
            # No documented hard limit; self-throttle conservatively.
            (300, dt.timedelta(minutes=1)),
            provider=ReccoBeatsAPIClient.provider_name,
        )
        # ... same RETRY_POLICY + hooks shape as Spotify

    async def audio_analysis(self, *, isrcs: list[str] | None = None,
                             spotify_track_ids: list[str] | None = None): ...
```

## Data Model

**No domain schema changes** beyond the cross-cutting `BirthSeed.trainer_id` (ADR-0001).

`Affinity.provider_id` already exists. `BirthSnapshot.provider_payloads` already stores per-provider payloads.

**New `app/settings.py` keys:**
- `SPOTIFY_CLIENT_ID: SecretStr | None`
- `SPOTIFY_CLIENT_SECRET: SecretStr | None`

**Trainer-token storage** (`trainer.spotify_refresh_token: SecretStr | None`) is covered in the linking plan, not here.

## Testing Plan

### Unit
- `SpotifyAPIClient` token cache: refreshes when expired, reuses while valid; bubbles 401 once for retry.
- `ReccoBeatsAPIClient` batched ISRC lookup: empty input → no HTTP; partial coverage → returns subset.
- Genre-family resolver: `["norwegian black metal", "bergen metal"]` → DARK + STEEL with correct weights.
- `determine_element_scores` against fixture payloads:
  - all-metal listener → STEEL primary, DARK secondary.
  - all-classical listener → PSYCHIC primary.
  - empty payload (cannot occur in practice due to precondition gate, but tested as defense in depth) → NORMAL fallback.
  - explicit-flag majority → DARK bonus fires.
- `calculate_intensity` produces:
  - high score for trainer with concentrated recent listening relative to window.
  - 0.5 fallback for single-day window (stdev undefined).
- Stat mapping correctly drops uncovered ReccoBeats tracks without crashing.

### Integration
- Provider runs end-to-end against captured Spotify + ReccoBeats response fixtures.
- `BirthSeed.fetch_snapshot` with `(ClimateProvider(), SoundProvider())` resolves both Affinities; both `provider_id`s persist.
- Replay determinism: same seed + same captured payload yields byte-identical Affinity.
- Precondition gate: birth request with `sound` in providers but no `trainer.spotify_refresh_token` fails validation before fetch is called.

### Regression
- Existing climate-only birth tests pass unchanged.
- `rebalance_existing_vibemons` tests pass with sound wired in.

## Observability

- Reuse `LoggingHook`, `RateLimiterHook`.
- Spotify rate limit: ~180 req/min rolling. Existing retry policy honors `Retry-After` on 429.
- ReccoBeats rate limit: no documented hard limit; self-throttle at 300/min.
- Per-fetch log fields: trainer_id (hashed), track_count, artist_count, reccobeats_coverage_ratio, unmatched_genre_count, window_days_in_recently_played.
- Tag all log lines with `provider="sound"`.

## Payload Retention (Spotify ToS posture)

Per locked decision 10:
- Reduced payload only — `name, explicit, release_date, duration_ms, isrc, played_at` per track; `name, genres` per artist; six ReccoBeats floats per covered track.
- **Popularity, follower count, and any other unused Spotify Content fields are never fetched, never stored, never derived.**
- Loose ToS reading acknowledged; revisit before any public launch.
- No automatic TTL deletion in v1. If a stricter posture becomes necessary post-launch, add a scheduled job that nulls Spotify-sourced fields >30 days old (derived signals remain intact).

## Preconditions / Dependencies

This plan **depends on** the following work landing first:

1. **ADR-0001: `BirthSeed` gains `trainer_id`.**
   Location: `docs/development/adr/0001-birth-seed-gains-trainer-id.md`.
   Adds `trainer_id` to `BirthSeed` and folds it into `_rng_seed_material`. Required for personal-only sound auth and as a latent bonus, fixes the dupe-birth risk where two trainers at the same coord+second would collide.

2. **Trainer-Spotify linking plan.**
   Location: `docs/development/plans/trainer-spotify-linking-plan.md`.
   OAuth Authorization Code redirect flow, `trainer.spotify_refresh_token` storage, token refresh helpers. Sound provider assumes `trainer.spotify_refresh_token` exists.

3. **Provider-picker UX** (mentioned but out of scope).
   Per-birth trainer selection of which providers to invoke. Without this, sound has no production invocation path. Sound provider code itself doesn't gate on the UX — it just expects to appear in `BirthSeed.providers` when invoked.

## Rollout

1. ADR-0001 lands (trainer_id in BirthSeed).
2. Trainer-Spotify linking plan lands (OAuth + token storage).
3. Bootstrap script + initial `genre_anchors.json` + `genre_families.json` ship as a separate PR for review of the genre→element flavor decisions in isolation.
4. Sound provider package lands. All tests pass against fixtures.
5. Dev shadow-birth: opt sound into a test trainer's births; inspect Affinity output across varied listening fingerprints.
6. Balance tuning pass: use `rebalance_existing_vibemons` against shadow births to tune ramp thresholds, intensity sigmoid steepness, NORMAL fallback weight.
7. Provider-picker UX lands.
8. Open sound provider to all linked trainers.
9. Document provider in `CONTEXT.md` if any new domain terms surface (none anticipated; provider fits inside existing `Provider`/`Signal`/`Affinity`/`Birth Seed` definitions).

## Open Questions

Most original open questions are resolved. Remaining:

1. **ReccoBeats coverage in practice.** Documented as ~70-90% for typical catalogs but unverified for niche/non-English listeners. If coverage is materially worse (<50%) for a real user, the stat block could be dominated by a small biased subset. Mitigation: log coverage ratio per birth; alert if median falls below threshold during shadow.
2. **Recently-played blend weight.** Plan suggests ~20% influence on stats vs ~80% from top_tracks. With ReccoBeats giving recently-played tracks real audio-feature impact, this weight may want to tune *up*. Defer to balance tuning pass.
3. **Spotify app extended-quota approval.** Default app registration in 2026 might not even permit `me/top` and `me/player/recently-played` without extended quota review. Confirm before building.
4. **ReccoBeats project longevity.** Newer community project, single point of dependency. If it disappears, the entire stat-mapping architecture loses its data source. Acceptable v1 risk; document a fallback path (frozen AcousticBrainz, or self-host ReccoBeats dataset snapshot).
5. **Genre anchor curation.** ~180 hand-anchored decisions (10 per element × 18 elements) is a real flavor design exercise. Worth a focused PR with the bootstrap script's output for review before lock.

## Notes for Future Expansion

- ListenBrainz support folded into same `sound/` provider for users who prefer open-source scrobbling.
- Last.fm scrobble enrichment as supplementary listening-history source for trainers with longer histories than Spotify exposes.
- Mood-tag enrichment via Last.fm folksonomy → element-scoring bonuses.
- AcousticBrainz frozen snapshot as fallback layer if ReccoBeats coverage proves insufficient for pre-2022 catalog.
- Self-host ReccoBeats dataset mirror once coverage stabilizes (removes external dependency).
- Cache by `(trainer_id, ISO-day)` — listening fingerprint is stable within a day. Defer until birth-rate per trainer justifies it.
