# Lifecycle staging migration (`manifested` -> `armed`/`awakened`)

## Status
Accepted

## Context
Current implementation and tests use lifecycle states `born`, `christened`, `manifested`.
The roadmap and domain context now target staged readiness with `born`, `christened`, `armed`, `awakened`.

Without an explicit migration ADR, roadmap implementation can drift between vocabulary and runtime behavior.

## Decision
Replace single `manifested` readiness with staged readiness:
- `armed`: battle-ready assets complete.
- `awakened`: full presentation assets complete.

Lifecycle remains an asset-realization state model, not ownership workflow state.

## Policy
1. Required lifecycle progression is monotonic: `born -> christened -> armed -> awakened`.
2. Candidate review requires `christened` minimum.
3. Battle entry and encounter reveal require `armed` minimum.
4. Full owned presentation and non-battle emotes require `awakened`.
5. Lifecycle transition guards are centralized in lifecycle policy constants and guard functions, not duplicated in service methods.

## Compatibility and migration
1. Add a temporary compatibility adapter period where persisted `manifested` rows are read as `awakened`.
2. During adapter period, writes must use only the new enum values.
3. Backfill script rewrites existing `manifested` rows to `awakened`.
4. Remove compatibility adapter after one release cycle once no `manifested` rows remain.

## Implementation notes
1. Define explicit required asset sets for `christened`, `armed`, and `awakened` in one lifecycle constants module.
2. Split lifecycle policy (guarding and required-set checks) from lifecycle realization I/O (generation/upload).
3. Keep service API unchanged while internal lifecycle adapters migrate.

## Consequences if adopted
- Improves interface depth for lifecycle and encounter preparation.
- Requires enum, policy, migration, and test updates.
- Enables clearer prewarm and reveal behavior without conflating all readiness under one state.

## Implementation Tasks
- [ ] Update lifecycle enum values in [`backend/app/types.py`](/C:/projects/vibemon/backend/app/types.py).
- [ ] Add lifecycle required-asset constants for `christened`/`armed`/`awakened` in [`backend/app/data_store/const.py`](/C:/projects/vibemon/backend/app/data_store/const.py) or a new lifecycle policy constants module.
- [ ] Split lifecycle guard/policy logic from realization I/O in [`backend/app/lifecycle/vibemon.py`](/C:/projects/vibemon/backend/app/lifecycle/vibemon.py).
- [ ] Update service lifecycle expectations in [`backend/app/services/vibemon_service.py`](/C:/projects/vibemon/backend/app/services/vibemon_service.py).
- [ ] Add compatibility adapter for legacy `manifested` reads and remove after backfill.
- [ ] Add a backfill script to rewrite persisted lifecycle values under [`backend/scripts/`](/C:/projects/vibemon/backend/scripts).
- [ ] Update lifecycle/service tests in [`backend/tests/test_vibemon_service.py`](/C:/projects/vibemon/backend/tests/test_vibemon_service.py).
