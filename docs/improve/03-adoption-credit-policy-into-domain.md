# 03 — Adoption plan + Generation Credit policy: push decisions into domain

**Status:** implemented — `crew.plan_adoption` owns the full adoption decision (slot + release + `CrewFull`); workflow `_adoption_plan` now only locks/fetches and applies. Credit reserve/consume/release were already domain-owned, unchanged.
**Priority:** high (pairs with 01)
**Vocabulary:** module / interface / seam / depth / locality / leverage per `improve-codebase-architecture` LANGUAGE.md; domain terms per `docs/development/CONTEXT.md`.

## Files involved

- `vibemon/backend/app/workflows/candidate.py` — `_adoption_plan` (lines ~156–193), `_reserve_credit` (lines ~196–224)
- `vibemon/backend/app/domains/trainer/` — `crew.select_adoption_slot`, `credits.reserve_generation_credit`
- `vibemon/backend/app/domains/adoption/`

## Problem

This is the "pure function extracted for testability, but the real bugs hide in how it's called" pattern. The pure domain functions exist:

- `crew.select_adoption_slot(owned_count, used_slots, release_slot)`
- `credits.reserve_generation_credit(row, now=now)`

…but the decision is actually made by ~68 LOC of workflow glue around them:

- The workflow queries owned vibemon rows (`with_for_update`), computes `used_slots`, looks up the release target, and only then calls the domain function.
- `CrewFull` is raised in the workflow (`if len(rows) >= crew.MAX_CREW_SIZE and release is None`), not by the domain policy — the rule about when a **Crew** is full lives outside the **Crew** module.
- The `_AdoptionPlan` result is a workflow-private class, not a domain concept.
- Credit reservation interleaves trainer locking, row fetching, and the domain call.

There is no **locality**: **Adoption** policy is split between a domain function and workflow glue, and testing the real decision requires mocking storage.

## Solution

Domain owns the full decision; workflow only fetches state and applies the result.

- Workflow fetches rows (locking stays in the workflow — locking is storage concern) and hands the domain a complete picture: owned vibemon summaries, release target, credit row, now.
- Domain (likely `domains/adoption`, drawing on `domains/trainer` crew rules) returns an adoption plan — slot, release action — or raises `CrewFull` itself. The plan becomes a domain type.
- Same shape for **Generation Credit**: domain decides reserve/consume/release given the credit row; workflow performs the fetch/lock/flush around it.

The interface between workflow and domain becomes: "here is the state, give me the decision."

## Benefits

- **Locality:** `CrewFull`, `MAX_CREW_SIZE`, and slot selection all live where **Crew** lives. **Generation Credit** semantics live in one domain module.
- **Tests:** adoption and credit rules become testable with plain values — no DB mocks, no session fixtures. Edge cases (full crew with release, slot reuse, double reserve) become table-driven domain tests.
- **Leverage for 01:** the Candidate Review module (plan 01) shrinks to fetch → decide → apply, making that consolidation cleaner.

## Notes / dependencies

- Do before or together with plan 01.
- Strengthens ADR-0001's intent that `domains/` owns game rules. No conflicts.
