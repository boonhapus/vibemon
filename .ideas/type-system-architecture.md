# Type System Architecture

**Status:** Accepted direction; implementation tracked in roadmap

## Why this exists

Type relationships should inform more than battle damage resolution. The main product value is better move assignment quality, clearer team-building feedback, and safer long-term balance tuning.

## Direction

- Keep `ELEMENT_CHART` as the source of truth for offensive relationships.
- Derive additional structures (coverage, weaknesses, resistances) from that source.
- Treat type-system changes as game-wide backend behavior across assignment, battle logic, and balance surfaces.

## Boundaries

- No progression/evolution coupling in v1 of this track.
- Backend-only implementation for this pass; defer trainer-facing/frontend surfaces.
- Weighting constants should be centralized and treated as balance-tuning knobs.

## Canonical task tracker

Implementation tasks are maintained in:
- `.plans/ROADMAP.md` -> `Type System Expansion (Deferred Build Track)`
