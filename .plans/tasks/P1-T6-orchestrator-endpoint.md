# P1-T6 — Orchestrator & Generate Endpoint

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T1, P1-T2, P1-T3, P1-T4, P1-T5
**Depends on this:** P1-T7, P2-T1, P5-T1

---

## Objective

Wire everything together: the orchestrator dispatches providers, merges results, runs the engine pipeline, generates both player and enemy payloads, and returns them through `POST /api/v1/generate`.

## Tasks

1. **Create `backend/app/engine/orchestrator.py`**
   - `async def generate(request_body) -> dict` — the top-level function
   - Build `GenerationContext` from the request
   - Determine active providers: iterate `PROVIDER_REGISTRY`, activate if the provider's required token is in `auth_tokens` (Weather always active)
   - `asyncio.gather(*[p.fetch(ctx) for p in active_providers], return_exceptions=True)`; collect only **`SourceData`** successes, skip **`BaseException`** outcomes (per-provider silent failure; does not cancel siblings)
   - Call `merge_source_data` on results
   - Call `compute_stats`, `generate_visual_dna`, `generate_moves`, `generate_name`
   - Assemble `VibemonPayload` with `stat_origins` map
   - Generate enemy via `generate_enemy(context)` — Weather-only, BST-scaled
   - Return `{"player": player_payload, "enemy": enemy_payload}`

2. **Implement `generate_enemy(context)`**
   - Construct enemy-specific `GenerationContext` with deterministic `user_id`:
     `f"enemy_{timestamp:%Y%m%d%H}_{round(lat,1)}_{round(lon,1)}"`
   - Fetch from `WeatherProvider` only
   - Build payload, then apply `scale_enemy_stats` against player BST

3. **Create `backend/app/routes/generate.py`**
   - `POST /api/v1/generate` route handler
   - Parse request body (validate `latitude`/`longitude` present or return 422)
   - Call orchestrator
   - Use cattrs to unstructure the response
   - Set `fallback: true` flag if all enrichment providers failed

4. **Implement move generation stub**
   - Create `backend/app/engine/moves.py` with `generate_moves(stats, seed) -> list[Move]`
   - For Phase 1, implement only the move pool for the elements that Weather can produce (Fire, Water, Ice, Grass, Ground)
   - Include signature move selection logic and the weighted selection algorithm from the design doc

5. **Update health endpoint**
   - Extend `GET /health` to ping Open-Meteo and report provider reachability

6. **Write integration test**
   - POST a valid request with lat/lon → verify 200 response with both `player` and `enemy` payloads
   - Verify all required fields are present in both payloads
   - POST without lat/lon → verify 422

## Acceptance Criteria

- `POST /api/v1/generate` with `{"user_id": "test", "latitude": 51.5, "longitude": -0.1, "auth_tokens": {}}` returns a full `GenerateResponse` with both player and enemy
- Enemy `user_id` is deterministic for the same city/hour
- Missing location returns 422
- Provider failure does not crash the endpoint

## Files Created

```
backend/app/
  engine/
    orchestrator.py
    moves.py
  routes/
    generate.py
tests/
  test_orchestrator.py
  test_generate_endpoint.py
```
