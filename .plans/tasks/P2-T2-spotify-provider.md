# P2-T2 — Spotify Provider (Backend)

**Phase:** 2 — Spotify Integration
**Dependencies:** P1-T6 (orchestrator), P2-T1 (frontend sends token)
**Depends on this:** P2-T3

---

## Objective

Implement the `SpotifyProvider` that fetches a user's recent listening history from Spotify, then enriches tracks with BPM and genre data from MusicBrainz and Last.fm.

## Important

The Spotify Audio Features API was deprecated in November 2024. **Do not call the `audio-features` endpoint.** All acoustic data comes from MusicBrainz (primary) and Last.fm (fallback).

## Tasks

1. **Create `backend/app/providers/spotify.py`**
   - Subclass `VibemonProvider`; `source_id = "spotify"`
   - Activate when `"spotify"` key is present in `auth_tokens`

2. **Fetch recent tracks from Spotify**
   - `GET https://api.spotify.com/v1/me/player/recently-played?limit=50`
   - Extract: track name, artist name, album name, played_at timestamp
   - Calculate: track count in last 7 days, average listening hour, unique artist count

3. **Enrich with MusicBrainz**
   - For each unique track (deduplicate by name+artist), query MusicBrainz:
     `GET https://musicbrainz.org/ws/2/recording?query=recording:{track}+artist:{artist}&fmt=json&limit=1`
   - Extract BPM from `isrcs` → recording → releases → media
   - Respect rate limit: 1 request/second (use `asyncio.sleep` or a semaphore)
   - Implement an in-memory dict cache keyed by `(track, artist)` to avoid repeat lookups within the same request

4. **Enrich with Last.fm (fallback)**
   - If MusicBrainz returns no BPM/tags for a track, query Last.fm:
     `GET https://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key={LASTFM_API_KEY}&artist={artist}&track={track}&format=json`
   - Extract top tags for mood and genre inference
   - `LASTFM_API_KEY` from environment variable

5. **Map to `SourceData`**
   Follow the provider mapping table exactly:
   - Average BPM (normalised 60–180) → `speed_factor`
   - BPM < 80 → `defense_factor` boost
   - Unique genre count (normalised 1–10) → `sp_attack_factor`
   - Genre-specific boosts to `attack_factor` and `sp_defense_factor`
   - Track count in 7 days (normalised 1–50) → `hp_factor`
   - Mood tags → element votes (dark→Dark, energetic→Electric, chill→Water, aggressive→Fire)
   - Average listening hour 22h–4h → Dark vote bonus
   - Derive `hue_primary` from energy/valence using `derive_hue()` function

6. **Implement `derive_hue(energy, valence) -> float`**
   - energy = average of normalised BPM + proportion of energetic genre tags
   - valence = ratio of positive to negative mood tags
   - Formula from design doc

7. **Register in `PROVIDER_REGISTRY`**

8. **Write tests**
   - Mock Spotify, MusicBrainz, Last.fm responses
   - Verify stat factor calculations
   - Test MusicBrainz failure → Last.fm fallback
   - Test both MusicBrainz and Last.fm failure → partial data still returned

## Acceptance Criteria

- With a valid Spotify token, the provider returns a `SourceData` with stat factors derived from real listening data
- MusicBrainz rate limit is respected
- Failure of any enrichment API does not crash the provider
- `stat_origins` entries trace back to specific listening metrics

## Files Created

```
backend/app/providers/spotify.py
tests/test_spotify_provider.py
```
