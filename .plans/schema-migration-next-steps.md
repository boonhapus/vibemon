# Schema Migration Next Steps

**Status date:** 2026-05-17  
**Current state:** Plan B migration and core follow-ups are completed and committed.

## Completed Work

1. Migration checkpoint committed.
2. `.scripts/battle_debug.py` updated to new `identity` + `vibemon_move` schema shape.
3. Provider balance analyzer repaired for post-affinity-table schema.
4. Monstore deletion wiring added for app-owned asset row deletes, with focused tests.
5. Provider move catalog registration implemented:
   - `VibeProvider.moves()` interface
   - `ClimateProvider.moves()` implementation
   - shared move catalog sync/upsert utility
   - generator path seeds provider moves before births/rebirth by default
6. Legacy migration script removed:
   - `.scripts/migrate_to_new_schema.py` deleted by design.

## Remaining Work

## 1. Provider Snapshot Versioning (Deferred)

**Goal:** Persist provider version metadata with snapshot payloads so replay behavior can be audited and guarded when providers change.

Steps:

1. Add a stable provider version field to `VibeProvider` (for example `schema_version`).
2. Add snapshot metadata storage for provider versions (DB column and/or JSON metadata alongside payloads).
3. Update `BirthSeed.fetch_snapshot()` to persist provider version metadata.
4. Update `BirthSnapshot.regenerate()` to:
   - expose version info during replay
   - warn on version mismatch
   - keep replay compatible for old snapshots with no metadata.
5. Add tests for:
   - new snapshots storing versions
   - legacy snapshots replaying without failure
   - mismatch warning path.
6. Document provider version bump rules.

Acceptance criteria:

- New snapshots record provider identity + version.
- Old snapshots still replay.
- Version mismatch is detectable and surfaced.

## 2. Optional Follow-up Hardening

1. Decide whether to commit or ignore `.pre-commit-config.yaml` (currently untracked).
2. Optionally add a small CLI/readme note for provider move seeding defaults and `--no-seed-provider-moves`.

