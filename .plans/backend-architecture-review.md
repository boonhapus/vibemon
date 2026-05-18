# Backend Architecture Review: Vibemon

**Date:** May 17, 2026  
**Status:** Approved Strategic Roadmap  
**Target:** Improved Maintainability, Testability, and Frontend Readiness

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
*   **Language Alignment:** Ensure `docs/LANGUAGE.md` accurately reflects the "Service vs. Lifecycle" distinction.
*   **Vibemon Read Model:** Define the Pydantic schemas for the "public-facing" Vibemon, including identity, stats, lifecycle, ownership, aesthetic colors, and fetchable asset URLs. Asset URLs may be signed/temporary; persisted identity should remain the asset ref/object key metadata.

### Phase 2: The VibemonService
*   **Implementation:** Create `app/services/vibemon_service.py` covering the `birth`, `christen`, `manifest`, and `adopt` workflows.
*   **Orchestration:** Consolidate any current CLI/script generator orchestration into this service. Do not depend on a `.scripts/vibemon_generator.py` path existing; treat scripts as callers to replace or simplify, not as the source of truth.
*   **Persistence:** Implement transaction-aware upserts for Vibemon and its associated aesthetic/asset records.
*   **Dependencies:** Accept injectable provider, GenAI, and asset/object-store dependencies so tests can run without external APIs.
*   **Tests:** Cover `birth`, `christen`, `manifest`, and `adopt` with fakes. Tests should verify lifecycle transitions, persisted rows, asset refs, and idempotent reruns where applicable.

### Phase 3: Move Catalog & Read Service
*   **Implementation:** Create `MoveCatalogService` to provide a queryable interface for the frontend.
*   **Separation of Concerns:** Ensure the catalog service remains data-oriented, deferring executable behavior resolution to the battle engine's runtime registry.

### Phase 4: Contextual Schema Distribution
*   **Refactor:** Once service boundaries are stable, split `app/schema.py` into domain-specific modules:
    *   `app/domain/vibemon.py` (Core Identity/Aesthetic)
    *   `app/domain/moves.py` (Declarative Move/Effect schemas)
    *   `app/domain/seed.py` (Birth inputs)
*   Maintain `app/schema.py` as a thin compatibility layer during the transition.

### Phase 5: API Layer Integration
*   **Wrapping:** Wrap the Service layer in a RESTful API (e.g., Litestar) to expose the "Internal API" to the Svelte frontend.

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

1. Add `app/services/`.
2. Add `VibemonService` with dependency injection and no HTTP framework coupling.
3. Add a public/read schema for a Vibemon response.
4. Wrap existing lifecycle functions rather than rewriting them.
5. Persist the resulting Vibemon, identity, moves, asset refs, trainer ownership, and lifecycle state through existing ORM models/helpers.
6. Add fake-backed tests for service behavior.

Acceptance criteria:

*   A caller can invoke service methods without importing ORM models, lifecycle modules, or GenAI clients directly.
*   Tests can run without real GenAI, real provider HTTP calls, or real remote object storage.
*   `birth` creates a persisted born Vibemon from provider affinities/snapshots.
*   `christen` persists generated name, preview asset refs, and `christened` lifecycle state.
*   `manifest` persists sheet/pose asset refs and `manifested` lifecycle state.
*   `adopt` assigns trainer ownership and triggers/queues manifestation according to the current synchronous implementation.
*   The service returns a read model suitable for a future API route.
