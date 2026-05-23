# Spotify / Sound Provider Plan (Draft)

## Goal
Add third `VibeProvider` deriving `Affinity` from the **soundtrack** of birth — what the trainer's account is listening to (or, lacking auth, what the trainer's market is listening to) at `seed.timestamp`. Runs alongside `ClimateProvider` and the planned `GeographyProvider`. Never replaces them.

## Why a separate provider, not a climate/geography extension
- Climate signals are *atmospheric* (sky). Geography signals are *physical place* (ground). Sound signals are *cultural/personal* (taste).
- A trainer in Reykjavík streaming Norwegian black metal and one streaming Icelandic ambient at the same coordinate, same hour, should produce visibly different creatures. Neither climate nor geography can express that.
- Spotify's genre vocabulary maps cleanly onto element flavor — metal→STEEL, classical→PSYCHIC, folk→GRASS, hip-hop→FIGHTING — closing flavor gaps that climate/geography fudge with proxies.
- Keeps single-source-of-truth per provider for replay and rate limiting.

## Scope
- In scope:
  - New `app/providers/sound/` package mirroring `app/providers/climate/`.
  - One concrete `SoundProvider(VibeProvider)`.
  - One thin async Spotify Web API client (`SpotifyAPIClient(niquests.AsyncSession)`) with OAuth (Client Credentials + optional Authorization Code), `LoggingHook`, `RateLimiterHook`.
  - `data/moves.json` of sound-flavored moves.
  - Element scoring + stat mapping + intensity formula tuned for music, not weather or place.
  - Settings additions: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_PROVIDER_ENABLED`, optional `SPOTIFY_REFRESH_TOKEN` per trainer.
  - Tests under `vibemon/backend/tests/app/providers/sound/` using captured fixture payloads.
- Out of scope (v1):
  - Any reliance on the **2024-deprecated** endpoints. See "Deprecation Wall" below.
  - Full OAuth Authorization Code redirect server. v1 ships **client-credentials** path (anonymous market data) as default and **bring-your-own refresh-token** as opt-in.
  - Track-level audio analysis (deprecated). No tempo/key/loudness/danceability/energy/valence.
  - Caching layer (genre catalog is stable; defer until measured).
  - Cross-provider deconfliction beyond existing `filter_element_types`.

## The Deprecation Wall — what is dead vs alive (2024-11)

Spotify removed access for new apps to a broad set of endpoints in Nov 2024. Plan **must not depend** on these.

| Endpoint | Status | v1 use |
|---|---|---|
| `GET /audio-features/{id}` | **dead** for new apps | none |
| `GET /audio-analysis/{id}` | **dead** | none |
| `GET /recommendations` | **dead** | none |
| `GET /artists/{id}/related-artists` | **dead** | none |
| `GET /browse/featured-playlists` | **dead** | none |
| `GET /browse/categories` and category playlists | **dead** | none |
| 30-second preview URLs on track objects | **dead** (null) | none |
| `GET /search` (track/artist/album/playlist) | **alive** | core |
| `GET /artists/{id}` (genres, followers, popularity) | **alive** | core |
| `GET /artists/{id}/top-tracks` | **alive** | core |
| `GET /tracks/{id}` (popularity, markets, explicit, release date) | **alive** | core |
| `GET /albums/{id}` | **alive** | flavor |
| `GET /markets` | **alive** | utility |
| `GET /me/top/{type}` (user auth) | **alive** | opt-in personal |
| `GET /me/player/recently-played` (user auth) | **alive** | opt-in personal |
| `GET /me/player/currently-playing` (user auth) | **alive** | opt-in personal |
| `GET /playlists/{playlist_id}` (specific ID known to caller) | **alive** | flavor |
| `GET /users/{user_id}/playlists` | **alive** | opt-in personal |

**Consequence**: the provider cannot read "energy" or "valence" off a track. Element scoring must be built from **genres + popularity + release-year + market breadth + explicit flag + follower count**. These are the surviving continuous + categorical signals.

## Locked Product Decisions (proposed — open for review)
1. Sound is a **peer** of climate and geography, default-enabled when `SPOTIFY_CLIENT_ID` is configured. If credentials absent, provider is skipped (not failed) for that birth — climate/geography still produce an `Affinity`.
2. `name = "sound"`. Persisted in `Affinity.provider_id`. Provider package directory is `sound/` (not `spotify/`) so future sources — Last.fm scrobbles, Apple Music, ListenBrainz — can fold in under the same provider without rename.
3. **Replay determinism**: `fetch()` snapshots the full Spotify JSON (track list, artist list with genres, popularities) so `synthesize()` is pure against the captured set.
4. Async like climate. `niquests.AsyncSession` subclass. Multiple parallel fetches via `asyncio.gather` (we are not paywalled by Spotify rate limits the way climate is by Open-Meteo).
5. **Two input modes**, selected at runtime by what's configured on the seed:
   - **Personal mode** (preferred when refresh token present): `me/top/tracks` (medium_term) + `me/player/recently-played` since `seed.timestamp - 6 weeks`. Mirrors climate's 6-week window for parity.
   - **Market mode** (default fallback): search for a deterministic "ambient catalog" query (e.g. top tracks in trainer's ISO-3166 market via `search?type=track&market=XX` sorted by popularity) keyed off `seed.geo_coords → market`.
6. Six continuous sound signals route to base stats. **Stat mapping must not duplicate climate or geography mappings.**
7. Provider owns its own move pool. Move IDs prefixed `sound.*`. `universal.tackle` + `universal.breaking_point` reused via base class loader.
8. Intensity for sound = "how unusual is this listening fingerprint" — high when genres are narrow + niche (low average artist popularity); low when broad mainstream pop. Sigmoid like climate.

## Genre → Element Mapping (proposed)

Spotify exposes a flat list of genre tags per artist (e.g. `["black metal", "norwegian metal"]`). Element scoring is a *substring/tag-prefix* match against a curated `GenreFamily` lookup, accumulated across all artists in the listening window, weighted by track count.

| Element | Genre prefixes (illustrative; final list TBD) |
|---|---|
| NORMAL | `pop`, `dance pop`, `adult contemporary` |
| FIRE | `metalcore`, `flamenco`, `mariachi`, `latin heat` |
| WATER | `ambient`, `chillwave`, `lo-fi`, `surf` |
| GRASS | `folk`, `bluegrass`, `americana`, `acoustic` |
| ICE | `cold wave`, `nordic ambient`, `minimal techno`, `iceland` regional |
| FLYING | `synthwave`, `dream pop`, `shoegaze`, `post-rock` |
| FIGHTING | `hardcore hip-hop`, `drill`, `trap`, `aggressive` |
| GROUND | `desert blues`, `stoner rock`, `dub` |
| STEEL | `industrial`, `metal`, `death metal`, `djent` |
| FAIRY | `j-pop`, `kawaii`, `hyperpop`, `bubblegum` |
| POISON | `noise`, `power electronics`, `harsh` |
| PSYCHIC | `classical`, `modern classical`, `minimalism`, `ambient academia` |
| DARK | `darkwave`, `gothic`, `black metal`, `doom` |
| GHOST | `dungeon synth`, `funeral doom`, `dark ambient`, `witch house` |
| BUG | `psytrance`, `idm`, `glitch`, `drum and bass` |
| ROCK | `classic rock`, `hard rock`, `grunge`, `punk` |
| DRAGON | `progressive metal`, `symphonic metal`, `epic` |
| ELECTRIC | `edm`, `electro`, `techno`, `house` |

Curated dict lives in `const.py` as `_GENRE_FAMILIES: dict[VibemonTypeT, tuple[str, ...]]`. Scoring is `prefix-match` on each artist's genre list, weighted by that artist's track count in the listening window.

**Six chosen continuous signals routed to stats** (must not duplicate climate or geography):

| Stat | Sound signal | Rationale |
|---|---|---|
| HP | total minutes listened in window (log-scaled) | endurance of taste |
| Attack | mean track popularity (0–100) | cultural mass / impact |
| Defense | genre cohesion (1 − genre entropy) | how locked-in the taste is |
| Sp. Attack | distinct-artist count (log-scaled) | informational breadth |
| Sp. Defense | mean artist follower count (log-scaled) | scene insulation |
| Speed | release-year recency (mean release year, normalized) | how current the listening is |

Climate maps temperature/wind/elevation/radiation/precipitation/wind. Geography maps population density / road density / building density / amenity diversity / green ratio / transport reach. Sound's six are orthogonal to both.

## Architecture Overview
1. `BirthSeed` (already carries lat/lon, timestamp, trainer id) is passed to provider.
2. `SoundProvider.fetch(seed)`:
   - Resolve `market` from `seed.geo_coords` via reverse-lookup (reuse geography provider's reverse-geocode if landed; otherwise fall back to `GET /markets` membership table).
   - If `seed.trainer.spotify_refresh_token` is set → **personal mode**:
     - `asyncio.gather` of: `me/top/artists?time_range=medium_term`, `me/top/tracks?time_range=medium_term`, `me/player/recently-played?after={seed.timestamp - 6w}`.
   - Else → **market mode**:
     - `asyncio.gather` of: `search?q=year:{Y}&type=track&market={M}&limit=50` (popularity-sorted), then for top-N tracks fetch `artists/{ids}` (batched, max 50 per call) to harvest genres.
   - Snapshot full JSON into payload dict.
3. `SoundProvider.synthesize(seed, payload)`:
   - Reduce to canonical lists: `tracks`, `artists` (deduped, with genres + popularity + followers).
   - Build `Signal` objects via `app.providers.helpers.Signal`. Min/med/max per signal calibrated against a captured corpus of 50+ diverse seeds (see Tuning section).
   - Two-stage element scoring: continuous block (genre-weighted) + categorical bonuses (explicit flag → DARK, single-genre lock → matching element bonus).
   - Pick starter moves via reused `_starter_move_weights` + `_pick_starter_moves` helpers — extracted to `app.providers.helpers` if not already shared.
   - Build `Affinity` with `provider_id="sound"`.
4. Wire into `rebalance_vibemon` defaults: `providers=(ClimateProvider(), GeographyProvider(), SoundProvider())`.

## File Layout

```
vibemon/backend/app/providers/sound/
├── __init__.py
├── api.py             # SpotifyAPIClient(niquests.AsyncSession), token mgr
├── const.py           # GenreFamily mapping, market lookup, tier thresholds
├── provider.py        # SoundProvider(VibeProvider)
└── data/moves.json    # sound-flavored move catalog
```

Mirrors climate exactly.

## Thin Spotify Client — Sketch

```python
class SpotifyAPIClient(niquests.AsyncSession):
    """
    Fetches listening + catalog data from Spotify Web API.

    Built only against the post-2024-deprecation surface. No audio-features,
    no recommendations, no related-artists.

    Further reading:
      https://developer.spotify.com/documentation/web-api
    """

    provider_name = "spotify.web_api"

    def __init__(self, client_id: str, client_secret: str, **session_opts):
        RATE_LIMITER = RateLimiterHook(
            # Spotify enforces a rolling 30s window; documented ceiling ~180 req/min.
            (180, dt.timedelta(minutes=1)),
            provider=SpotifyAPIClient.provider_name,
        )
        RETRY_POLICY = niquests.RetryConfiguration(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503],
            allowed_methods=["GET"],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        hooks = cast(Any, LoggingHook(provider=...) + RATE_LIMITER)
        super().__init__(
            base_url="https://api.spotify.com/",
            hooks=hooks, retries=RETRY_POLICY,
            **session_opts,
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: _BearerToken | None = None
        self._user_refresh_token: str | None = None

    async def _ensure_token(self) -> None:
        """Client-credentials flow OR refresh-token flow, cached until expiry."""

    async def search_tracks(self, q: str, market: str, limit: int = 50) -> niquests.Response: ...
    async def artists(self, ids: list[str]) -> niquests.Response: ...   # batched, 50 max
    async def me_top(self, kind: Literal["artists", "tracks"], time_range: str) -> niquests.Response: ...
    async def me_recently_played(self, after_ms: int) -> niquests.Response: ...
```

Token refresh is the only thing that diverges from climate's client. Encapsulate in `_ensure_token` called from a `pre_request` hook so the public methods stay flat.

## Data Model
- `Affinity.provider_id` already exists; `BirthSnapshot` already stores per-provider payloads. **No schema change** for the snapshot.
- New `app.settings.SETTINGS` keys: `SPOTIFY_CLIENT_ID: SecretStr | None`, `SPOTIFY_CLIENT_SECRET: SecretStr | None`, `SPOTIFY_PROVIDER_ENABLED: bool = False`.
- Optional `Trainer.spotify_refresh_token: SecretStr | None` if/when personal mode is wired. v1 may ship market-mode only and defer trainer-level token storage.

## Move Catalog Sketch
~30 moves, themed by element. Examples (final list TBD):
- `sound.bass_drop` (ELECTRIC, level 1)
- `sound.feedback_wail` (STEEL, level 5)
- `sound.requiem` (GHOST, level 10)
- `sound.power_chord` (ROCK, level 1)
- `sound.fugue` (PSYCHIC, level 10)
- `sound.kick_drum` (FIGHTING, level 5)
- `sound.lullaby` (FAIRY, level 1)
- `sound.dissonance` (POISON, level 5)

## Testing Plan
### Unit
- `SpotifyAPIClient` token cache: refreshes when expired, reuses while valid.
- Genre-family resolver: `["norwegian black metal", "bergen metal"]` → DARK + STEEL with correct weights.
- `determine_element_scores` against fixture payloads:
  - all-metal listener → STEEL primary, DARK secondary
  - all-classical listener → PSYCHIC primary
  - empty payload (new user, no listening history) → NORMAL fallback
  - explicit-flag majority → DARK bonus fires
- `calculate_intensity` produces high score for narrow-niche listener, ~0.5 for mainstream pop.
- Signal mapping covers all six stats with no division-by-zero on empty artist list.

### Integration
- Provider runs end-to-end against captured Spotify response fixtures (market mode + personal mode).
- `BirthSeed.fetch_snapshot` with `(ClimateProvider(), GeographyProvider(), SoundProvider())` resolves all three Affinities and persists all three `provider_id`s.
- Replay determinism: same seed + same captured payload yields byte-identical Affinity.
- Provider gracefully skips birth when credentials missing — climate/geography still succeed.

### Regression
- Existing climate-only and climate+geography birth tests pass unchanged.
- `rebalance_vibemon` tests pass with all three providers wired in.

## Observability
- Reuse `LoggingHook`, `RateLimiterHook`.
- Spotify rate limit: rolling 30s window, documented ~180 req/min ceiling. Log 429 + `Retry-After` header captures; existing retry policy honors it.
- Log per-fetch: mode (personal/market), market code, track count, artist count, genre count, fetched-from-cache flag (when caching added).
- Tag log lines with `provider="sound"` to match climate/geography.

## Rollout
1. Land package + move catalog behind `SETTINGS.SPOTIFY_PROVIDER_ENABLED`, default off.
2. Ship **market mode only** in v1. Personal mode behind separate `SPOTIFY_PERSONAL_MODE_ENABLED` flag.
3. Add tests, fixtures, fakes (record-and-replay against a test Spotify app).
4. Shadow birth in dev: all three providers fetch, only climate+geography persist, sound's `Affinity` is logged for inspection.
5. Tune genre-family table + signal min/med/max against 50+ varied seeds (mix of markets, listening fingerprints).
6. Flip flag in staging; verify replay parity.
7. Production rollout with flag.
8. Personal mode wired in v2 with trainer-token storage + OAuth redirect endpoint.
9. Document provider in `CONTEXT.md` vocabulary section.

## Open Questions
1. **Market mode signal quality**: "what's popular in market X right now" is *very* coarse. Two trainers in the same country get nearly identical birth fingerprints in market mode. Acceptable v1 cost, or block on personal mode?
2. **Genre-family table maintenance**: Spotify mints new genre tags constantly (~6000 today, growing). Static curated dict will drift. Strategy — quarterly manual refresh, automated tag-clustering, or LLM-assisted classification on first sighting?
3. **Time range parity with climate**: climate uses 6 weeks. Spotify's `me/top` exposes `short_term` (4w), `medium_term` (6m), `long_term` (~years). Pick `medium_term` for richer signal, or `short_term` for tighter parity?
4. **Listening window for `recently-played`**: API caps at 50 most recent items regardless of `after` cursor. Plan B if 50 isn't enough for a representative window — page back? accept the cap?
5. **Trainer-token storage**: SecretStr in DB plus refresh on use. Worth a separate ADR before personal mode lands?
6. **Provider order in `rebalance_vibemon`**: deterministic order matters for replay. Climate, then geography, then sound? Document the ordering invariant.
7. **Intensity composition across three providers**: `Affinity.intensity` is a single field — same open question as geography plan, now sharper. Per-provider intensity, max, or blend?
8. **Spotify ToS**: caching responses, persisting genre data, redistributing — re-read terms before storing payload snapshots long-term.

## Notes for Future Expansion
- Last.fm scrobble enrichment under the same `sound/` provider — gives play-count history Spotify won't expose for non-personal mode.
- ListenBrainz as open-data fallback when Spotify credentials absent (community scrobble database, no auth).
- Track-level vibes via **MusicBrainz + AcousticBrainz** (community successor to dead audio-features), keyed by ISRC.
- Cache by `(market, ISO-week)` for market mode — listening trends change weekly, not by-the-second.
- Self-host genre-family classifier (small embedding model over genre tag corpus) to remove static dict drift.
