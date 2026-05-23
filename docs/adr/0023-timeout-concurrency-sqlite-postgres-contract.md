# Timeout concurrency contract (SQLite local vs Postgres production)

## Status
Accepted

## Context
Roadmap concurrency goals include first-success-wins semantics for candidate timeout vs trainer actions and safe concurrent cleanup workers.
Local execution currently uses SQLite for testing; production target is Postgres.

Lock semantics differ materially between SQLite and Postgres, so one implicit rule-set is not sufficient.

## Decision
Adopt an explicit two-profile concurrency contract:
- Local SQLite profile: functional correctness and invariant checks, not authoritative lock-behavior simulation.
- Production Postgres profile: authoritative row-lock, race-resolution, and worker-concurrency semantics.

## Policy
1. First-success-wins is the canonical transition rule for pending candidate reviews.
2. All review state transitions must be conditional on current status being `pending`.
3. Timeout cleanup is idempotent; processing an already-resolved review is a no-op.
4. Trainer action and timeout races must resolve to exactly one successful transition.

## SQLite profile (local)
1. Validate invariant correctness and transition policy behavior.
2. Do not claim lock-order or worker-concurrency guarantees from SQLite behavior.
3. Run single-worker cleanup by default in local scripts.
4. Enforce persistence invariants directly with SQLite-safe `CHECK`/unique constraints:
   - Vibemon disposition/trainer/team-slot shape.
   - Candidate-review status/resolution coherence.

## Postgres profile (production target)
1. Use row-level lock semantics for transition commands.
2. Timeout cleanup worker path uses `FOR UPDATE SKIP LOCKED` batch acquisition.
3. Transition writes use conditional predicates to prevent duplicate resolution under races.
4. Multi-worker cleanup is allowed only after Postgres concurrency test suite passes.

## Verification requirements
1. SQLite test suite: functional tests for timeout/adopt/reject ordering and idempotent cleanup.
2. Postgres integration suite: concurrent worker and conflicting-command race tests.
3. Release gate: production concurrency features require passing Postgres race tests.

## Consequences if adopted
- Cleaner expectations for local testing scope.
- Explicit production-hardening checklist for concurrency before deployment.
- Lower risk of roadmap claims drifting from actual runtime guarantees.

## Implementation Tasks
- [x] Make review transition writes conditional on `pending` in [`backend/app/services/vibemon_service.py`](/C:/projects/vibemon/backend/app/services/vibemon_service.py).
- [ ] Keep local cleanup default single-worker in [`backend/scripts/cleanup_holds.py`](/C:/projects/vibemon/backend/scripts/cleanup_holds.py).
- [ ] Add explicit production-path timeout batching semantics (`FOR UPDATE SKIP LOCKED`) for Postgres in service/repository layer.
- [x] Add SQLite functional race/invariant tests in [`backend/tests/test_vibemon_service.py`](/C:/projects/vibemon/backend/tests/test_vibemon_service.py), [`backend/tests/test_stale_holds.py`](/C:/projects/vibemon/backend/tests/test_stale_holds.py), and [`backend/tests/test_persistence_invariants.py`](/C:/projects/vibemon/backend/tests/test_persistence_invariants.py).
- [ ] Add Postgres concurrency integration tests under `backend/tests/` (new test module).
- [ ] Document release gate requiring Postgres race test pass before multi-worker cleanup enablement.

## Postgres hardening checklist (follow-up)
- [ ] Add `FOR UPDATE SKIP LOCKED` timeout-batch path.
- [ ] Add transition-update predicates that no-op if status is no longer `pending`.
- [ ] Add concurrent adopt/reject/timeout integration tests on Postgres.
- [ ] Add concurrent cleanup worker integration tests on Postgres.
- [ ] Keep multi-worker cleanup disabled until Postgres tests pass in CI.
