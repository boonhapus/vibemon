# P1-T4 — Stat Engine (Seeds, Stats, Merging, Elements)

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T2
**Depends on this:** P1-T5, P1-T6

---

## Objective

Build the stat computation engine: deterministic seeding, factor-to-stat conversion, multi-provider merging, and element resolution.

## Tasks

1. **Create `backend/app/engine/stats.py`**

2. **Implement `make_seed(user_id, source_id) -> int`**
   - UUID5 with namespace `6ba7b810-9dad-11d1-80b4-00c04fd430c8`
   - `int(uuid.uuid5(namespace, f"{user_id}:{source_id}").hex, 16)`

3. **Implement `factor_to_stat(factor, rng) -> int`**
   - `MIN_STAT = 30`, `MAX_STAT = 230`
   - Apply ±10% seeded variance
   - Clamp to [1, 255]
   - Missing factors default to 0.5

4. **Implement `compute_stats(merged: SourceData, seed: int) -> VibemonStats`**
   - Create `random.Random(seed)` for deterministic variance
   - Convert each factor → stat
   - Resolve primary element: highest total vote weight
   - Resolve secondary element: runner-up if its weight ≥ 50% of the winner's

5. **Implement `merge_source_data(sources: list[SourceData]) -> SourceData`**
   - Average non-`None` scalar fields across all providers
   - Sum element vote weights by element name, sort descending
   - Join flavour texts with ` | `

6. **Implement enemy BST scaling**
   - `scale_enemy_stats(player_stats, enemy_stats) -> VibemonStats`
   - If enemy BST is outside ±15% of player BST, scale all stats proportionally
   - Preserve distribution, clamp each stat to [1, 255]

7. **Write tests**
   - `make_seed` determinism: same inputs → same output
   - `factor_to_stat` range validation and determinism
   - `merge_source_data` with 1, 2, 3 providers — verify averaging
   - Element resolution: primary, secondary, and no-secondary cases
   - BST scaling: within band (no-op), below band, above band

## Acceptance Criteria

- All functions are deterministic given the same seed
- `compute_stats` produces stats in [1, 255] for any valid input
- `merge_source_data` correctly averages and ignores `None` fields
- Element secondary is only assigned when runner-up ≥ 50% of winner weight

## Files Created

```
backend/app/engine/stats.py
tests/test_stats.py
```
