# Vibemon Roadmap

**Status:** Active  
**Last updated:** May 18, 2026  
**Purpose:** Implementation checklist for engineering execution.

## 1) Baseline (Done)

- [x] Service foundation in `app/services/VibemonService`.
- [x] Candidate review + disposition model (`owned|wild|expired`, review as separate state).
- [x] Credit-day + generation-hold flow with timeout cleanup.
- [x] Atomic full-party release/adopt slot swap.
- [x] Public read model with trainer-private review fields.
- [x] Local reset/cleanup scripts (`make db-reset`, `make db-cleanup`).

## 2) Architecture Hardening (Do Next)

### 2.1 Transition Policy Extraction
- [x] Add `app/policies/vibemon_transitions.py`.
- [x] Move command guard logic out of `VibemonService` into explicit transition checks.
- [x] Add focused tests for legal/illegal transition matrix.

### 2.2 Lifecycle Policy/IO Split
- [x] Add `app/lifecycle/policy.py` for required-assets and allowed-lifecycle transitions.
- [x] Add `app/lifecycle/realizer.py` for IO (genai/storage) behind injected adapters.
- [x] Keep `VibemonService` as facade while delegating implementation.

### 2.3 Remove Import-Time Runtime Construction
- [x] Remove import-time global GenAI client construction.
- [x] Pass runtime dependencies/config via constructors/factories.
- [x] Add startup wiring tests proving injectability with fakes.

### 2.4 Domain Module Split
- [x] Split `app/schema.py` into `app/domain/{birth,vibemon,move,read_models}.py`.
- [x] Keep temporary `app/schema.py` re-export shim for migration safety.
- [x] Update imports incrementally with no behavior changes.

### 2.5 Read Model Assembler + Config
- [x] Add service-internal read-model assembler seam.
- [x] Move signed URL TTL into centralized config constant (default 15m).
- [x] Add tests for signed URL policy behavior.

### 2.6 Persistence/Concurrency Contract
- [x] Enforce candidate-review/disposition invariants with SQLite-safe constraints now.
- [x] Document SQLite vs Postgres concurrency guarantees in code/docs.
- [x] Add Postgres follow-up checklist for lock/race semantics hardening.

## 3) Wild Encounter Slice (Build After 2.x)

### 3.1 Wild Eligibility + Geography
- [x] Implement wild query eligibility filter: exclude under-review and expired.
- [x] Implement geohash precision-5 bucket scoping.
- [x] Add sparse expansion: local -> ring-1 (8 neighbors) -> ring-2.

### 3.2 Supply + Selection
- [x] Generate christened wild supply when eligible pool is below threshold.
- [x] Revalidate disposition before final encounter selection.
- [x] Implement v1 selector: bucket priority -> strength band -> adjustment multiplier -> uniform pick.

### 3.3 Manifest Latency Hiding
- [x] Support lazy manifest for wild candidates during prewarm/preparation.
- [x] Add encounter-reveal hook to hide cold manifest latency.

### 3.4 Wild Expiration
- [x] Add expiration job: mark wild vibemon `expired` after 30 days since last actual encounter.
- [x] Reset expiration clock on battle start/completion encounters.
- [x] Keep asset cleanup as separate retention workflow.

### 3.5 Encounter Adjustment + Strength Matching
- [x] Implement trainer-specific encounter multipliers with decay window (1-3 days).
- [x] Wire outcome multipliers: reject/timeout `0.00x`, run `0.30x`, defeat `0.50x`, win-no-adopt `0.75x`.
- [x] Centralize strength constants and implement:
- [x] Member strength = actual level-scaled stat total.
- [x] Party strength = avg + 25% max + 10% total.
- [x] Wild target = 45% of party strength, acceptance band 70%-140%.

## 4) API/Frontend Readiness

- [x] Define service error mapping contract (typed domain exceptions -> interface error codes).
- [x] Expose API read models with trainer-private review metadata only to reviewer.
- [x] Implement timeout-facing fields/copy support (`Timed out`, resolved timestamp).
- [x] Keep API framework choice deferred until service seams stabilize.

## 5) Move Content Externalization (Deferred Build Track)

### 5.1 Schema + Identity Preparation
- [x] Add stable `Move.id` support in domain schema while keeping compatibility with current `name`/`flavor_text`.
- [x] Define move content contract for external files (JSON v1) and document required/optional fields.
- [x] Add validation rules for unique IDs and enum correctness across provider move sets.

### 5.2 Loader + Validation Layer
- [x] Add `backend/app/content/moves.py` loader that reads provider JSON and returns typed `Move` objects.
- [x] Enforce strict validation (reject unknown fields, invalid enums, malformed effects/conditions).
- [x] Add test fixtures for valid, invalid, and duplicate-id datasets.
- [x] Loader failure policy: reject invalid moves individually, continue loading valid moves, and emit actionable provider/developer fix reports.

### 5.3 Full Adoption Migration
- [x] Convert all provider move sources from Python-defined moves to JSON content in the same migration wave.
- [x] Keep battle engine consumption typed (`Move`/`BattleMove`), with no engine-side raw JSON parsing.
- [x] Add compatibility bridge so existing Python move modules can coexist during migration.

### 5.4 Catalog + Tooling Integration
- [x] Ensure `MoveCatalogService` can serve moves loaded from JSON without behavior regressions.
- [x] Update move audit/balance tooling to read through the shared loader path.
- [x] Update generation/content tooling to emit JSON move definitions instead of Python source where applicable.
- [x] Update `.agents/skills/vibemon/move-generator` workflow/prompts so generated move outputs target the JSON move-content contract (not Python module emission).
- [x] Add/refresh tests or validation checks used by move-generator flows to verify generated JSON passes loader validation.
- [x] Testing scope (current phase): keep tests focused on isolated-change correctness for loader, schema validation, migration integrity, and catalog compatibility.
- [x] Testing scope (post-migration, pre-frontend): add a full-suite test initiative covering cross-provider catalog invariants, assignment distribution behavior, and end-to-end battle/type-system regressions.

### 5.5 Boundaries and Non-Goals (v1)
- [x] Do not add provider-authored executable callbacks.
- [x] Keep `script_id` as backend-owned first-party mapping only.
- [x] Defer localization infrastructure (`name_key`/`flavor_key`) until frontend i18n requirements are active.

## 6) Type System Expansion (Deferred Build Track)

### 6.1 Move Assignment Integration
- [x] Wire existing type bonus logic into move assignment path.
- [x] Add tests proving same-type preference and antagonistic penalty behavior.
- [x] Verify assignment outputs remain bounded/diverse after weighting changes.

### 6.2 Derived Type-Affinity Data
- [x] Build derived type-affinity structures from `ELEMENT_CHART` (covers, weak_to, resists).
- [x] Keep derivation code centralized under balance/domain utilities.
- [x] Add invariants/tests for chart reversals and derived consistency.

### 6.3 Coverage-Aware Assignment
- [x] Add coverage bonuses so assignments can fill defensive gaps, not only same-type preference.
- [x] Tune weighting constants behind centralized balance constants.
- [x] Add regression tests against over-concentration and antagonistic move rates.
- [x] Apply sweeping type-system changes in one coordinated rollout (assignment + battle logic), with isolated-change tests during implementation and full-suite hardening scheduled post-migration/pre-frontend.
- [x] Treat type-system rearchitecture as game-wide domain behavior (not move-local only), and align assignment, battle, and downstream balance surfaces together.
- [x] After type-system rearchitecture, regenerate the full move corpus so no legacy-generated move artifacts remain before validation/test runs.
- [x] Replace approved move catalog all-at-once after regeneration (no mixed old/new generation batches).

### 6.4 Read Model + UX Surface (Later Slice)
- [x] Define backend read-model fields needed for weakness/coverage UI.
- [x] Expose matchup summaries in API-facing shapes without coupling to frontend framework choices.
- [x] Keep initial UI scope to explanatory coverage/weakness display only.
- [x] Keep current type-system rearchitecture pass backend-only; defer trainer-facing UX/screens until post-migration pre-frontend full-suite phase.

### 6.5 Later Coupling (Explicitly Not v1)
- [ ] Defer progression/evolution coupling to type-system signals.
- [ ] Defer affinity-generation coupling changes until telemetry/balance loops are established.

## 7) Explicitly Deferred

- [ ] Catch mechanics (battle action semantics) remain deferred.
- [ ] Async candidate generation remains deferred; design tracked in `.ideas/async-candidate-generation-redis-docket.md`.
- [ ] PvP matchmaking remains deferred.

## Reference Files

- `docs/CONTEXT.md`
- `docs/adr/`
- `.plans/emote-animation-plan.md`
- `.ideas/async-candidate-generation-redis-docket.md`
