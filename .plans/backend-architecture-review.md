# Backend Architecture Review: Vibemon

**Date:** May 17, 2026  
**Status:** Approved Strategic Roadmap  
**Target:** Improved Maintainability, Testability, and Frontend Readiness

---

## 0. Progress Snapshot

### Completed

- [x] Merged glossary into `docs/CONTEXT.md`; removed `docs/LANGUAGE.md`.
- [x] Added ADRs for disposition, lifecycle asset gating, provider fetch/synthesize split, deterministic birth, battle events, move effects, wild pool rules, candidate review, generation credits, party slots, encounter matching, and deferred catch language.
- [x] Added `.plans/ROADMAP.md` with `/grill-with-docs` resume marker for unresolved decisions.
- [x] Existing code has provider `fetch()` / `synthesize()` split.
- [x] Existing code has deterministic `BirthSeed` RNG namespaces.
- [x] Existing code has monstore-backed asset refs and asset-row upsert helpers.
- [x] Existing code has lifecycle states `born`, `christened`, and `manifested`.
- [x] Existing code has battle turn events emitted from the battle engine.
- [x] Added `app/services/` and first-pass `VibemonService`.
- [x] Added persisted disposition, candidate-review metadata, generation-credit day/hold storage, and encounter-adjustment storage.
- [x] Added a public Vibemon read model with candidate-review and asset URL fields.
- [x] Added fake-backed service tests for candidate generation, credit release on failure, adoption, rejection, and timeout.

### Not Yet Implemented

- [ ] Recreate/reset local development data after schema changes; no backwards-compatible migration path is needed before users exist.
- [ ] Full generation-credit concurrency hardening beyond the in-session service path. Trainer/row locking and swap failure ordering improved on May 18, 2026; crash hold expiry remains open.
- [x] Atomic full-party adoption swap.
- [x] Release service workflow outside full-party adoption.
- [ ] Wild encounter selection, prewarming, expiration cleanup, catch mechanics, and PvP matching.

---

## 1. Executive Summary
The Vibemon backend is a data-driven system built on Python 3.14+ and Pydantic. It successfully decouples **Thematic Intent** (authored by Providers) from **Generic Mechanics** (executed by the Battle Engine). As the project transitions toward frontend integration, this document establishes a **Service-First** roadmap to resolve current maintainability bottlenecks—primarily monolithic schemas and dispersed lifecycle logic—without premature refactoring.

---

## 2. Core Architectural Pillars

### 2.1 Service-Oriented Orchestration
The primary evolution is the introduction of `app/services/` as the "Internal API." Services will own:
*   **Transaction Boundaries:** Coordinating database persistence and ORM loading.
*   **Dependency Injection:** Managing lifecycle-scoped clients for GenAI, storage (monstore), and external providers.
*   **Read Models:** Converting internal domain schemas and ORM rows into API-ready objects for the frontend.

### 2.2 Move Semantic Separation
To maintain the flexibility of provider-authored content, we maintain a strict boundary between three domains:
1.  **Authorship (Providers):** Author raw move data (name, type, power, effects).
2.  **Persistence & Catalog (MoveCatalogService):** A data-oriented service for syncing, querying, and serving move definitions.
3.  **Execution (Battle Engine & Script Registry):** The runtime layer that interprets declarative effects and resolves `script_id` references to first-party executable code.

### 2.3 Lifecycle State Machine
`app/lifecycle/` remains a dedicated layer for Vibemon state transitions (`BORN` -> `CHRISTENED` -> `MANIFESTED`). It provides the "state machine" logic (e.g., "what mutations occur during christening?"), while the `VibemonService` handles the I/O and persistence required to trigger those transitions.

---

## 3. Infrastructure & Dependency Management

### 3.1 GenAI and Client Lifecycle
*   **No Global Clients:** Eliminate import-time initialization of GenAI, audio, and image clients in `app/genai/client.py`.
*   **Service-Level Injection:** Clients should be instantiated or injected at the Service level. This enables isolated testing with fakes and ensures request-scoped configuration is possible.

### 3.2 Asset Management (monstore)
*   **Infrastructure, not Provider:** Object storage is a shared infrastructure concern. It remains behind the `monstore` abstraction, but access is moderated through the `AssetService` to handle URL generation and cleanup.

---

## 4. Implementation Roadmap

### Phase 1: Establish Language and Read Models
*   [x] **Language Alignment:** Ensure `docs/CONTEXT.md` accurately reflects the "Service vs. Lifecycle" distinction.
*   [x] **Vibemon Read Model:** Define the Pydantic schemas for the "public-facing" Vibemon, including identity, stats, lifecycle, ownership, aesthetic colors, and fetchable asset URLs. Asset URLs may be signed/temporary; persisted identity should remain the asset ref/object key metadata.

### Phase 2: The VibemonService
*   [x] **Implementation:** Create `app/services/vibemon_service.py` covering candidate generation, `birth`, `christen`, `manifest`, `adopt`, `reject`, and review-timeout workflows.
*   [x] **Orchestration:** Consolidate any current CLI/script generator orchestration into this service. Do not depend on a `.scripts/vibemon_generator.py` path existing; treat scripts as callers to replace or simplify, not as the source of truth.
*   [x] **Persistence:** Implement transaction-aware upserts for Vibemon, disposition, candidate-review metadata, generation-credit accounting, and associated aesthetic/asset records.
*   [x] **Dependencies:** Accept injectable provider, GenAI, and asset/object-store dependencies so tests can run without external APIs.
*   [ ] **Tests:** Cover candidate generation, `birth`, `christen`, `manifest`, `adopt`, `reject`, and review timeout with fakes. Tests should verify lifecycle transitions, disposition transitions, candidate review invariants, generation credit holds/consumption, persisted rows, asset refs, and idempotent reruns where applicable.

### Phase 3: Move Catalog & Read Service
*   [ ] **Implementation:** Create `MoveCatalogService` to provide a queryable interface for the frontend.
*   [x] **Separation of Concerns:** Ensure the catalog service remains data-oriented, deferring executable behavior resolution to the battle engine's runtime registry.

### Phase 4: Contextual Schema Distribution
*   [ ] **Refactor:** Once service boundaries are stable, split `app/schema.py` into domain-specific modules:
    *   `app/domain/vibemon.py` (Core Identity/Aesthetic)
    *   `app/domain/moves.py` (Declarative Move/Effect schemas)
    *   `app/domain/seed.py` (Birth inputs)
*   Maintain `app/schema.py` as a thin compatibility layer during the transition.

### Phase 5: API Layer Integration
*   [ ] **Wrapping:** Wrap the Service layer in a RESTful API (e.g., Litestar) to expose the "Internal API" to the Svelte frontend.

---

## 5. Decision Log & Constraints
*   **Service-First Sequencing:** Do not refactor schemas until the Service Layer implementation reveals the natural data clusters.
*   **Event-Oriented Engine:** The `GameEngine` produces `TurnEvents` for frontend playback; preserve this event-driven output even while the engine mutates in-memory state.
*   **No Speculative Scripting:** Do not build complex `script_id` resolution infrastructure until a concrete move requires custom first-party code.
*   **API Framework Deferred:** Do not assume Litestar or any specific HTTP framework until the dependency is explicitly added and accepted. Services should be framework-agnostic.
*   **Lifecycle vs. Adoption:** Adoption is trainer ownership assignment. It may trigger manifestation work, but it is not itself a lifecycle state.

---

## 6. First Implementation Slice
For a new engineer or agent, the first concrete slice should be narrow:

1. [x] Add `app/services/`.
2. [x] Add `VibemonService` with dependency injection and no HTTP framework coupling.
3. [x] Add persisted disposition and candidate-review metadata. Disposition is `owned`, `wild`, or non-playable `expired`; a missing gameplay disposition is valid only while an active candidate review exists.
4. [x] Add generation-credit accounting: three credits per trainer per day, one active generation job at a time, credit hold during generation, consume only when a christened candidate is shown.
5. [x] Add a public/read schema for a Vibemon response that includes lifecycle, disposition, candidate-review state where relevant, ownership, identity, stats, colors, and fetchable asset URLs.
6. [x] Wrap existing lifecycle functions rather than rewriting them.
7. [x] Persist the resulting Vibemon, identity, moves, asset refs, trainer ownership, disposition, candidate review, and lifecycle state through existing ORM models/helpers.
8. [x] Add fake-backed tests for service behavior.

Acceptance criteria:

*   A caller can invoke service methods without importing ORM models, lifecycle modules, or GenAI clients directly.
*   Tests can run without real GenAI, real provider HTTP calls, or real remote object storage.
*   Candidate generation creates a persisted born/christened Vibemon from provider affinities/snapshots and opens candidate review for the requesting trainer.
*   `christen` persists generated name, preview asset refs, and `christened` lifecycle state.
*   `manifest` persists sheet/pose asset refs and `manifested` lifecycle state.
*   `adopt` resolves candidate review or future wild ownership into `owned`, assigns trainer ownership, preserves existing core assets, and triggers/queues manifestation when needed.
*   `reject` resolves candidate review into `wild`, starts the trainer-specific encounter adjustment at `0.00x`, and does not discard the Vibemon.
*   Review timeout after 24 hours from shown time resolves unresolved candidates into `wild`; the deadline is authoritative even if cleanup runs late.
*   Generation credits are held during generation, consumed only when a christened candidate is shown, and released on failure.
*   The service returns a read model suitable for a future API route.
*   Wild encounters, catch mechanics, prewarming, encounter weighting, expiration cleanup, and PvP matching remain later slices.

---

## 7. Implementation Checklist

### 7.1 Domain and Persistence

- [x] Add a persisted Vibemon disposition field with values `owned`, `wild`, and non-playable `expired`.
- [x] Allow missing gameplay disposition only while an active candidate review exists.
- [x] Add candidate-review metadata for shown candidates: Vibemon id, reviewing trainer id, shown timestamp, status/resolution, and timeout deadline.
- [x] Keep `trainer_id` as ownership only; candidate review references the reviewing trainer separately.
- [x] Add generation-credit accounting for three credits per trainer per day.
- [x] Add generation-credit hold state so only one generation job can run for a trainer at a time.
- [x] Add history/event records for candidate shown, adopted, rejected, timed out, released, and expired.
- [x] Add trainer/Vibemon encounter adjustment storage for later encounter weighting, with initial support for rejection/timeout starting at `0.00x`.

### 7.2 Service Layer

- [x] Create `app/services/`.
- [x] Add `VibemonService` with injected provider, GenAI, asset/object-store, clock, and random dependencies.
- [x] Implement candidate generation: reserve credit, fetch/synthesize providers, birth, christen, persist candidate review, consume credit on shown success, release hold on failure.
- [x] Implement candidate adoption: reject timed-out candidates first, assign `owned`, set `trainer_id`, preserve assets, manifest if needed, and resolve review.
- [x] Implement candidate rejection: resolve review to `wild`, clear ownership, set wild-pool timing, and create trainer-specific encounter adjustment.
- [x] Implement review-timeout resolution: candidates older than 24 hours become `wild`; timeout is authoritative even if cleanup runs late.
- [x] Implement release: transition `owned` to `wild`, reset wild expiration baseline to release time, preserve progression, moves, history, and core assets.
- [x] Implement full-party adoption swap atomically: release selected party Vibemon, adopt new Vibemon, and assign freed battle slot in one transaction.

### 7.3 Read Models

- [x] Add a public Vibemon read model with identity, stats, lifecycle, disposition, ownership, party slot, colors, and asset URLs.
- [x] Include candidate-review state only where relevant to the reviewing trainer.
- [x] Return asset URLs as fetchable/signed values while persisting asset refs/object keys.
- [ ] Exclude candidate-review and expired Vibemon from future wild-encounter read/query surfaces.

### 7.4 Lifecycle and Assets

- [x] Keep lifecycle as asset-realization state only: `born`, `christened`, `manifested`.
- [x] Keep existing lifecycle functions wrapped initially rather than rewritten wholesale.
- [ ] Ensure lifecycle transitions advance only after required asset refs exist.
- [ ] Ensure adoption and release do not regenerate or degrade existing core manifestation assets.
- [ ] Defer wild prewarm, encounter preparation, and catch mechanics to later implementation slices.

### 7.5 Tests

- [x] Test successful candidate generation consumes one daily credit only after a christened candidate is shown.
- [x] Test failed candidate generation releases the hold and does not consume a credit.
- [x] Test one active generation job per trainer, while allowing multiple unresolved shown candidates up to available daily credits.
- [x] Test candidate adoption is free, resolves review, sets `owned`, assigns ownership, and manifests only when needed.
- [x] Test candidate rejection resolves to `wild` and creates a `0.00x` encounter adjustment.
- [x] Test candidate timeout after 24 hours from `shown_at` resolves to `wild` even if cleanup runs late.
- [x] Test adoption after timeout is rejected and first resolves the candidate to `wild`.
- [x] Test full-party adoption requires an atomic release/adopt slot swap.
- [x] Test release preserves level, XP, moves, history, and assets while resetting wild expiration baseline.
- [ ] Test encounter queries exclude under-review and expired Vibemon once encounter surfaces are introduced.
