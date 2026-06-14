# Architecture deepening plans

Output of an architecture review (2026-06-11) hunting **deepening opportunities** — refactors that turn shallow modules into deep ones: a lot of behaviour behind a small interface. Goals are testability and AI-navigability. Vocabulary: *module / interface / seam / adapter / depth / locality / leverage* from the `improve-codebase-architecture` skill; domain terms from `docs/development/CONTEXT.md`.

## Status

Plans 01–05 are implemented (2026-06-13); their write-ups were removed once shipped. See git history for the changes:

| Plan | Outcome | Commit |
|---|---|---|
| 04 — Fake asset generator adapter | Offline `FakeVibemonAssetGenerator`, selected via `VIBEMON_GENAI__FAKE_ASSETS` | `926c015` |
| 02 — Lifecycle realization module | `MaterializeVibemon` is the deep module; the `asset_realization` facade was slimmed, then dissolved entirely in favour of direct calls | `43fceda` + facade-removal follow-up |
| 03 — Adoption + credit policy into domain | `crew.plan_adoption` owns the adoption decision | `2cc5901` |
| 01 — Candidate Review module | Four review helpers folded into `candidate.py` | `3a0a6db` |
| 05 — Public projection read model | `ReadModelAssembler` collapsed into `public_projection.public_vibemon` | `8344040` |

## Open

- [06 — Provider Warning contract](06-provider-warning-contract.md) — **deferred** (2026-06-13). Warnings are already a typed field on `Affinity` and testable today; the `BirthProvider` port rewrite across six providers plus Birth Snapshot replay is high-surface for low marginal value. Revisit when a concrete need arises (e.g. a new provider that must emit warnings).
