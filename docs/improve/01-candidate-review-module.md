# 01 — Candidate Review module: fold five shallow workflow files into one deep module

**Status:** proposed
**Priority:** high (second after 02+04)
**Vocabulary:** module / interface / seam / depth / locality / leverage per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/workflows/candidate.py` (~225 LOC) — main orchestrator
- `vibemon/backend/app/workflows/candidate_finalize.py` (~27 LOC)
- `vibemon/backend/app/workflows/candidate_refresh.py` (~27 LOC)
- `vibemon/backend/app/workflows/candidate_action.py` (~37 LOC)
- `vibemon/backend/app/workflows/candidate_manifest.py`
- `vibemon/backend/app/workflows/wild_disposition.py` (~46 LOC)

## Problem

The Candidate flow (generate → **Candidate Review** → adopt/reject/timeout → **Owned**/**Wild**) is spread across five-plus modules. The helper files fail the deletion test: each is a pass-through over repositories or deeper workflows — deleting one would not concentrate complexity, just relocate a few lines. A caller (HTTP route, script frontend) must know which of five files owns which step of the flow. The helpers exist as a symptom: `candidate.py` is too wide in scope, so slivers were shaved off into named files instead of being made private.

Specific shallow modules:

- `candidate_finalize.py` reads `reference_detected_facing`, calls `reference_facing`, returns.
- `candidate_refresh.py` calls `asset_realization.reprocess_display_assets`, reads facing, returns.
- `candidate_action.py` loads a vibemon, assembles a view, calls `public_projection`.
- `wild_disposition.py` holds two small functions (`mark_wild`, `release_to_wild`) that mutate storage rows directly — **Disposition** transitions living outside any cohesive home.

## Solution

One deep Candidate Review module whose public interface is the domain verbs:

- `generate(...)` — consume a **Generation Credit**, run **Birth**, open a **Candidate Review**
- `adopt(...)` — resolve review to **Owned**, plan **Battle Slot**, optional **Release**
- `reject(...)` — resolve review to **Wild**
- `resolve_timeout(...)` — apply **Candidate Review Timeout**, resolve to **Wild**

Everything currently in the helper files becomes private implementation (underscore functions or a private submodule). **Disposition** transitions used only by this flow live inside it; if `release_to_wild` is also needed by an independent Release flow, that stays a separate concern — check call sites before folding.

## Benefits

- **Locality:** every Candidate Review change, bug, and invariant lands in one file. The credit rollback try/except choreography is visible in one place.
- **Leverage:** callers see four verbs instead of a file map. HTTP routes and scripts shrink.
- **Tests:** the interface is the test surface. Today workflows have no direct tests (logic is tested through HTTP routes); a four-verb interface invites direct workflow tests for generate/adopt/reject/timeout paths.

## Notes / dependencies

- Pairs with plan 03 (adoption plan + credit policy into domain): doing 03 first or together shrinks what this module must orchestrate.
- No ADR conflicts. Strengthens ADR-0001 (workflows as transport-ignorant orchestration).
