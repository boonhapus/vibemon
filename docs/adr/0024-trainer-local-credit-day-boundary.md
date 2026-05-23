# Trainer-local generation credit day boundary

## Status
Accepted

## Context
Roadmap and context language target three generation credits per trainer per local day.
Current implementation behavior is effectively UTC-date keyed unless trainer-local timezone is explicitly supplied.

The product rule is clear, but the architecture lacks a locked source-of-truth for trainer-local day calculation.

## Decision
Define trainer profile timezone as the authoritative source-of-truth for generation-credit day boundaries.

## Policy
1. Credit windows reset at trainer-local midnight using trainer profile timezone.
2. Service commands requiring credit checks must receive a resolved trainer timezone from persistence, not request headers.
3. If trainer timezone is missing, generation command fails with a domain error (no silent UTC fallback).
4. Timezone changes apply to future credit windows only; current-day counters are not recomputed retroactively.
5. Daily cap remains three with no carry-over.

## Persistence contract
1. Trainer row stores an IANA timezone id.
2. Credit day rows continue using `credit_date` keyed by `(trainer_id, credit_date)`, where `credit_date` is computed in trainer-local timezone.
3. Optional audit columns can be added later (`timezone_used`, `window_start_utc`, `window_end_utc`) if needed for support tooling.

## Migration and rollout
1. Add trainer timezone field and backfill existing trainers with a configured default timezone for local development.
2. Update generation service to compute `credit_date` from trainer-local timezone.
3. Add tests covering timezone boundary behavior around midnight and DST transitions.
4. Remove any remaining UTC-date assumptions from generation credit logic.

## Consequences if adopted
- Makes generation-credit semantics deterministic and auditable.
- Aligns implementation with roadmap/product language.
- Requires small service and persistence contract updates before external API stabilization.

## Implementation Tasks
- [ ] Add trainer timezone field (IANA id) to [`backend/app/models.py`](/C:/projects/vibemon/backend/app/models.py).
- [ ] Add/update migration/reset path for trainer timezone in local DB tooling under [`.scripts/`](/C:/projects/vibemon/.scripts).
- [ ] Compute generation `credit_date` from trainer-local timezone in [`backend/app/services/vibemon_service.py`](/C:/projects/vibemon/backend/app/services/vibemon_service.py).
- [ ] Add domain error for missing trainer timezone in [`backend/app/errors.py`](/C:/projects/vibemon/backend/app/errors.py) and enforce in service.
- [ ] Add tests for midnight boundary and DST behavior in [`backend/tests/test_vibemon_service.py`](/C:/projects/vibemon/backend/tests/test_vibemon_service.py).
- [ ] Remove any UTC-date assumptions in generation-credit logic and test fixtures.
