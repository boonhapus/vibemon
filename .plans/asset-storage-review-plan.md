# Asset Storage Focused Review Plan

**Status date:** 2026-05-17  
**Branch context:** `feat/monstore-asset-storage` (squashed to one commit)

## 1. Review Objective

Perform a targeted code review of newly introduced asset storage behavior to confirm:

1. Asset blobs and DB metadata stay consistent across create, update, delete, rebirth, and lifecycle transitions.
2. Lifecycle transitions (`BORN -> CHRISTENED -> MANIFESTED`) are safe, idempotent, and do not permit partial invalid states.
3. Storage adapter behavior is correct across `file://`, `memory://`, and signable remote stores.
4. Failure behavior is explicit and acceptable (especially blob-delete failures and missing blob scenarios).
5. Tests cover critical invariants and expose likely regressions.

## 2. Review Intent and Success Criteria

This review is meant to find defects and regression risk, not style nits.

Success criteria:

1. Every asset-storage code path has been reviewed against a concrete invariant checklist.
2. Findings are categorized by severity with exact file references.
3. Uncovered risk areas are explicitly called out as test gaps.
4. We leave with a clear “ship/no-ship with conditions” recommendation for asset storage.

## 3. In-Scope Files

Primary scope (direct asset-storage behavior):

1. `backend/app/data_store/__init__.py`
2. `backend/app/data_store/assets.py`
3. `backend/app/data_store/const.py`
4. `backend/app/data_store/monstore.py`
5. `backend/app/data_store/schema.py`
6. `backend/app/data_store/types.py`
7. `backend/app/lifecycle/__init__.py`
8. `backend/app/lifecycle/vibemon.py`
9. `backend/app/models.py`
10. `backend/app/schema.py`
11. `backend/app/settings.py`
12. `backend/app/types.py`
13. `backend/app/sprite_store.py` (deleted; verify replacement completeness)
14. `backend/tests/test_data_store_assets.py`
15. `.scripts/cleanup_monstore.py`

Secondary scope (integration seams likely to affect asset behavior):

1. `.scripts/vibemon_generator.py`
2. `backend/app/genai/client.py`
3. `backend/app/genai/_image.py`
4. `backend/app/genai/utils.py`
5. `backend/app/plugins/api_hooks.py`
6. `backend/app/plugins/provider.py`

## 4. Detailed File-by-File Review Checklist

## 4.1 `backend/app/data_store/monstore.py`

Intent:
Validate object-store correctness, deterministic keying, and URL/read/delete semantics.

Checks:

1. Key derivation invariant:
   - `asset_key()` is deterministic, collision-safe for `vibemon_id + version + kind`.
   - Versioning model (`v1`) is explicit and stable.
2. Write/read parity:
   - `put()` metadata (`sha256`, `byte_size`, `content_type`) matches bytes actually written.
   - `get()` returns exact bytes and does not mutate payload.
3. URL behavior:
   - Unsignable schemes (`file`, `memory`) return predictable direct URLs.
   - Remote schemes require presigning and correct expiry handling.
4. Caching behavior:
   - `_store()` caching via `lru_cache` is acceptable with runtime config expectations.
   - Risk check: stale cache if settings are changed during process lifetime.
5. Deletion behavior:
   - `delete()` semantics understood for missing keys across providers.

Failure signals to look for:

1. Key/path ambiguity.
2. Store URL changes not reflected due to caching.
3. Blob lifecycle requiring assumptions not guaranteed by obstore providers.

## 4.2 `backend/app/data_store/assets.py`

Intent:
Validate DB-blob consistency management and cleanup semantics.

Checks:

1. Upsert correctness:
   - Correct row matching by `(vibemon_id, kind)`.
   - `created_at` preserved on update; `updated_at` refreshed.
   - Old blob key deleted only when key changes.
2. Delete behavior:
   - `delete_for_vibemon()` always removes DB rows even if blob deletes fail.
   - Warnings are emitted with enough context to reconcile failures.
3. Idempotency:
   - Re-running upsert with same key should avoid unnecessary delete calls.
4. Transaction boundaries:
   - Caller commit behavior is explicit and consistent.
   - No hidden commits inside helpers.
5. Safety with duplicates:
   - `delete_object_keys()` deduplicates keys.

Failure signals to look for:

1. Orphaned blobs from silent key replacement failures.
2. Inconsistent DB state if select/update/delete assumptions break under concurrency.

## 4.3 `backend/app/data_store/const.py`, `types.py`, `schema.py`

Intent:
Validate the asset vocabulary contract and metadata model used by all storage operations.

Checks:

1. `AssetKind` completeness and path semantics.
2. `ASSET_CONTENT_TYPES` one-to-one coverage assertion remains true.
3. Required asset sets for lifecycle stages are complete and non-contradictory.
4. `AssetRef` immutability/frozen semantics are intentional and useful.
5. Version defaults in `AssetRef` remain synchronized with key layout versioning.

Failure signals to look for:

1. Missing content type entries for newly added asset kinds.
2. Lifecycle requirements out of sync with generated artifacts.

## 4.4 `backend/app/lifecycle/vibemon.py`

Intent:
Validate lifecycle orchestration and state-transition safety around generated/stored assets.

Checks:

1. Transition gating:
   - `christen()` only advances after required preview assets exist.
   - `manifest()` only advances after required full asset set exists.
2. Idempotency and rerun behavior:
   - Re-calling `christen()`/`manifest()` on already transitioned entities behaves safely.
3. Failure modes:
   - Missing reference blob surfaces as explicit runtime error.
   - Partial generation failures do not incorrectly advance lifecycle state.
4. Concurrency assumptions:
   - TaskGroup/gather usage does not hide failed child tasks.
5. Asset write ordering:
   - Stored refs are attached to `aesthetic.assets` with correct kind mapping.
6. Ownership semantics:
   - `adopt()` behavior aligns with intended “manifest on ownership” contract.

Failure signals to look for:

1. Lifecycle state advanced before full asset requirements are met.
2. Partial asset writes with no cleanup/rollback strategy.

## 4.5 `backend/app/models.py`

Intent:
Validate relational schema support for asset storage and cleanup.

Checks:

1. `VibemonAsset` table constraints:
   - FK to `vibemon` and uniqueness by asset slot are correct.
2. Cascades and ownership:
   - Relationship cascades do not accidentally remove required metadata too early.
3. New schema relations:
   - `Vibemon`, `Identity`, `Trainer`, `VibemonMove`, `BirthSnapshot` changes do not break asset assumptions.
4. Index/check constraints:
   - Any new constraints do not conflict with asset update flows.

Failure signals to look for:

1. Constraint mismatch with upsert logic.
2. Deletion cascades that bypass intended blob cleanup path.

## 4.6 `backend/app/schema.py` and `backend/app/types.py`

Intent:
Validate read-model contract for asset refs, lifecycle semantics, and consumer-facing accessors.

Checks:

1. `Aesthetic.assets` map type and key/value integrity.
2. `url_for()` and `bytes_for()` behavior for absent refs.
3. Vibemon identity/lifecycle fields consistency with lifecycle module assumptions.
4. Move-count and lifecycle validation constraints are coherent with generation flows.

Failure signals to look for:

1. Schema methods implying availability when refs may be missing.
2. Lifecycle enum drift between schema and orchestration code.

## 4.7 `backend/app/settings.py` and deleted `backend/app/sprite_store.py`

Intent:
Verify safe migration from sprite-only storage to unified asset storage.

Checks:

1. Rename migration:
   - `sprite_store_url` -> `asset_store_url` is complete for all active code paths.
2. Validator behavior:
   - URL validation still enforces required store scheme correctness.
3. Deletion completeness:
   - No remaining imports/usages of deleted `sprite_store.py`.

Failure signals to look for:

1. Runtime config break for environments still setting old env var names.
2. Dead references to removed sprite store API.

## 4.8 `.scripts/cleanup_monstore.py`

Intent:
Validate operational recovery tool for drift between DB rows and object store.

Checks:

1. Safety guardrails:
   - Supports `file://` only and fails closed for other schemes.
2. Scan logic:
   - Correctly computes orphaned blobs and missing-blob DB rows.
3. Destructive mode:
   - `--delete-orphans` behavior is explicit and bounded to intended root.
4. Reporting:
   - Output is sufficient for operator audit and cleanup verification.

Failure signals to look for:

1. False positives/negatives in orphan detection.
2. Risky path handling or delete scope expansion.

## 4.9 `backend/tests/test_data_store_assets.py`

Intent:
Assess whether tests cover high-risk asset storage invariants.

Checks:

1. Covered:
   - DB row deletion despite blob delete failure.
   - old-key blob cleanup when upsert replaces key.
2. Missing likely tests:
   - No-op upsert with unchanged key.
   - multi-kind upserts and dedupe behavior.
   - lifecycle transition behavior coupled with storage writes.
   - URL signing behavior by scheme.

Failure signals to look for:

1. Critical invariants untested.
2. Tests that validate implementation details but miss behavior-level guarantees.

## 4.10 Secondary Integration Files

Intent:
Ensure upstream/downstream callers use asset storage correctly.

Checks:

1. `.scripts/vibemon_generator.py`:
   - Uses lifecycle + `ds_assets.upsert` consistently.
   - No stale assumptions from pre-monstore model shape.
2. `backend/app/genai/client.py`, `_image.py`, `utils.py`:
   - Output contracts match lifecycle expectations (reference bytes vs sheet bytes).
3. `backend/app/plugins/api_hooks.py`, `provider.py`:
   - Confirm changes are unrelated or note if they alter generation-side preconditions.

## 5. Review Execution Order

1. Core storage contract:
   - `data_store/types.py`, `const.py`, `schema.py`, `monstore.py`, `assets.py`.
2. Lifecycle orchestration:
   - `lifecycle/vibemon.py`, `schema.py`, `types.py`.
3. Persistence and migration:
   - `models.py`, `settings.py`, deleted `sprite_store.py`.
4. Operational and test safety:
   - `cleanup_monstore.py`, `test_data_store_assets.py`.
5. Integration sanity pass:
   - generator + genai + plugin seams.

## 6. Findings Output Format

When executing this review, report findings in this format:

1. Severity: `high`, `medium`, `low`.
2. File reference.
3. Risk statement.
4. Why this matters.
5. Minimal fix direction.
6. Missing test coverage (if applicable).

## 7. Explicit Non-Goals

1. Broad battle-balance logic review.
2. Style-only comments without behavioral impact.
3. Full provider ecosystem review outside asset lifecycle/storage coupling.

## 8. Exit Criteria

Review is complete only when:

1. All in-scope files above are examined.
2. Every checklist section is answered with pass/fail notes.
3. At least one explicit statement is made for:
   - DB/blob consistency confidence.
   - lifecycle transition safety confidence.
   - operational cleanup confidence.
4. Remaining risks are either:
   - accepted with rationale, or
   - converted into concrete follow-up tasks/tests.
