# P2-T3 — Complete Move Pools & Multi-Provider Merge Verification

**Phase:** 2 — Spotify Integration
**Dependencies:** P2-T2, P1-T6
**Depends on this:** P4-T1

---

## Objective

Complete the move pools for all 9 elements (Phase 1 only covered weather-producible elements) and verify that multi-provider merging produces visibly different Vibemons compared to weather-only.

## Tasks

1. **Complete move pools in `backend/app/engine/moves.py`**
   - Add full 8-move pools for all 9 elements: Fire, Water, Ice, Electric, Grass, Ground, Dark, Psychic, Normal
   - Each pool: 3 physical, 3 special, 2 status moves
   - Mark signature moves with `is_signature=True`
   - Copy move data exactly from the design doc tables

2. **Implement `generate_moves(stats, seed)` fully**
   - Always include the signature move
   - Guarantee at least 1 physical and 1 special via weighted selection
   - Fill the 4th slot from remaining candidates
   - Weighting: physical moves weighted by `attack/128`, special by `sp_attack/128`, status by `sp_defense/128`

3. **Verify multi-provider merge end-to-end**
   - Write an integration test that generates a Vibemon with weather-only, then with weather+spotify mock data
   - Assert that stats differ meaningfully
   - Assert that `source` field reflects active providers (e.g. `"spotify+weather"`)
   - Assert that `stat_origins` contains entries from both providers

4. **Complete syllable banks**
   - Ensure `names.py` has syllable banks for all 9 elements (~40 syllables each)

## Acceptance Criteria

- All 9 element move pools are defined with correct power/accuracy/effect values
- `generate_moves` returns exactly 4 moves including the signature
- A Spotify-enriched Vibemon is statistically different from a weather-only one

## Files Modified

```
backend/app/engine/moves.py
backend/app/engine/names.py
tests/test_moves.py
tests/test_multi_provider.py
```
