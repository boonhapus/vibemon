# 06 — Provider Warning path: make warnings testable per Provider

**Status:** proposed
**Priority:** medium
**Vocabulary:** module / interface / seam / depth / locality per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/domains/generation/types.py` — warning types
- `vibemon/backend/app/providers/*/` — each provider's `synthesize()` emits warnings
- `vibemon/backend/app/workflows/candidate.py` (~lines 49–63) — sole place warnings surface, attached to the **Candidate Review** via `provider_notes`
- `vibemon/backend/app/domains/generation/ports.py` — `BirthProvider` protocol

## Problem

**Provider Warnings** are a cross-cutting concern spanning domain (`generation/types`), each **Provider**'s `synthesize()`, and the candidate workflow. The interface doesn't carry them explicitly — they ride along inside the **Affinity** or surface only as `provider_notes` after a full **Birth**. Consequences:

- No isolated test exists for "Provider X with thin input Y yields warning Z." Testing a warning requires setting up a real provider, running birth, and inspecting the resulting **Candidate Review**. Integration-only coverage.
- Only the **Music Provider** has deep tests today (~770 LOC); warning behaviour for other providers is effectively unspecified.
- Per `CONTEXT.md`, warnings are non-fatal signals ("birth completed but some inputs were thin") — a contract worth stating in types, not convention.

## Solution

Make warnings an explicit part of the `synthesize()` interface contract: a typed return alongside the **Affinity** (e.g. result type carrying affinity + warnings), declared on the `BirthProvider` port. Each provider's warning conditions become unit-testable: feed a **Provider Observation** (thin/partial), assert the expected warnings. The birth workflow just aggregates warnings from all opted-in providers and attaches them to the **Candidate Review** — no per-provider knowledge.

## Benefits

- **Tests:** the interface is the test surface — each Provider's warning behaviour gets isolated, table-driven tests, independent of birth orchestration. Valuable given six providers exist and only Music is well-tested.
- **Locality:** what counts as a warning for a provider lives in that provider; aggregation policy lives in one place in the birth workflow.
- **Leverage:** the `BirthProvider` port becomes honest — warnings are visible in the contract instead of folklore.

## Notes / dependencies

- Touches the `BirthProvider` port — coordinate with **Birth Snapshot** replay: re-synthesis from persisted **Provider Observations** must reproduce warnings too (consistent with the rebalance-as-dev-tuning stance).
- No ADR conflicts; ADR-0002 (`trainer_id` on `BirthSeed`) unaffected.
