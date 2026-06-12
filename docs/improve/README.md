# Architecture deepening plans

Output of an architecture review (2026-06-11) hunting **deepening opportunities** — refactors that turn shallow modules into deep ones: a lot of behaviour behind a small interface. Goals are testability and AI-navigability. Vocabulary: *module / interface / seam / adapter / depth / locality / leverage* from the `improve-codebase-architecture` skill; domain terms from `docs/development/CONTEXT.md`.

Each plan is self-contained and can be picked up individually. Before implementing one, run a grilling session against it — these documents describe the problem and the shape of the solution, not the final interface design.

## Recommended order

| # | Plan | Priority |
|---|------|----------|
| 1 | [04 — Fake asset generator adapter](04-fake-asset-generator-adapter.md) | highest |
| 2 | [02 — Lifecycle realization module](02-lifecycle-realization-module.md) | highest |
| 3 | [03 — Adoption + credit policy into domain](03-adoption-credit-policy-into-domain.md) | high |
| 4 | [01 — Candidate Review module](01-candidate-review-module.md) | high |
| 5 | [05 — Public projection read model](05-public-projection-read-model.md) | medium |
| 6 | [06 — Provider Warning contract](06-provider-warning-contract.md) | medium |

## Why this order

**04 first because it de-risks everything after it.** The fake `VibemonAssetGenerator` adapter is the cheapest item on the list (one small new adapter, zero interface change) and it converts a hypothetical seam into a real one. That matters for sequencing: plan 02 restructures ~1,400 LOC of asset machinery, and you want interface-level tests for **Christen**/**Manifest** *before* moving that code, not after. The fake adapter is what makes those tests possible offline. Doing 04 first means 02 is a refactor under test instead of a refactor on faith.

**02 second because it's the largest depth win.** The asset realization machinery is the most fragmented subsystem in the codebase — seven files, criss-crossed imports, implicit ordering and implicit numpy/matte contracts. Collapsing it behind transition verbs (`christen`, `manifest`) buys the most leverage per unit of effort anywhere in the codebase, and with 04 landed it can be verified at the interface the whole way through.

**03 before 01 because it shrinks what 01 must absorb.** Plan 01 consolidates the candidate workflow family into one deep Candidate Review module. The biggest source of width in `candidate.py` today is the ~68 LOC of adoption-plan and credit-reservation glue. Plan 03 moves those decisions into the domain (`CrewFull` raised where **Crew** lives, credit semantics where **Generation Credit** lives), so when 01 folds the five files together, the result is a clean fetch → decide → apply orchestrator rather than a bigger pile of the same glue. 03 also pays for itself independently: adoption and credit rules become table-driven domain tests with no DB mocks.

**01 fourth, completing the candidate flow.** With domain decisions extracted (03), folding `candidate_finalize` / `candidate_refresh` / `candidate_action` / `candidate_manifest` / `wild_disposition` into one module with four verbs (generate, adopt, reject, resolve-timeout) is mostly mechanical. Doing it earlier would mean consolidating code that 03 is about to rewrite.

**05 and 06 last, in either order, because they're independent and smaller.** Plan 05 (public projection) is a maintainer-locality win, not a caller-leverage win — callers already have a one-call interface. Plan 06 (Provider Warning contract) touches the `BirthProvider` port and is worth doing before any serious investment in the non-Music providers, but nothing else on this list depends on it. Neither blocks nor is blocked by 01–04.

## Dependency summary

- **04 → 02**: 04 enables interface tests that make 02 safe. (04 can also land entirely standalone.)
- **03 → 01**: 03 shrinks the orchestration that 01 consolidates.
- **05, 06**: independent of everything; schedule opportunistically.

## ADR status

No plan conflicts with existing ADRs. Plans 01–03 actively strengthen ADR-0001 (domain-first architecture: `domains/` owns rules, workflows orchestrate). ADR-0002 (`trainer_id` on `BirthSeed`) is unaffected; plan 06 notes a coordination point with **Birth Snapshot** replay.
