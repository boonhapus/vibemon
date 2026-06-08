# Development Ideas

Exploratory design notes for features not yet (or only partially) implemented. Each idea follows the same narrative so you can scan any doc the same way.

## How to read an idea

| Field | Meaning |
| ----- | ------- |
| **Status** | `Idea` (exploratory), `Adopted` (decision made — see linked plan), `Deferred` (valid but blocked), `Superseded` (replaced elsewhere) |
| **Priority** | Rough urgency when we pick it up: `High` / `Medium` / `Low` / `—` (reference-only) |
| **Complexity** | Engineering + design cost estimate |
| **Area** | Which product slice this touches |
| **Related** | Other ideas, plans, or ADRs |

## Document shape

Every idea uses these sections **in order**. Omit a section only when it genuinely does not apply (e.g. provider ideas skip **Implementation** until one is scoped).

1. **Summary** — One short paragraph: what this is and why it matters.
2. **Problem** — The gap, pain, or constraint driving the idea.
3. **Concept** — High-level approach or thesis (before tables, schema, or code).
4. **Design** — Detailed mechanics, data model, UX, signals, catalog, etc. Use `###` subsections as needed.
5. **Implementation** — Phases, rollout, wiring, migration (when known).
6. **Open Questions** — Unresolved decisions.
7. **Success Criteria** — How we know the idea worked (when applicable).
8. **Anti-Goals** — Explicit non-goals (when applicable).

Provider ideas use a consistent **Design** subsection order:

`Data Sources` → `Secrets` → `Type Mapping` → `Signal Design` → `Intensity` → `Provider Notes` → `Moves` → `Proposed Structure` → `Wiring`

## Adding a new idea

Copy `_TEMPLATE.md`, fill metadata, and link related docs. Keep tuning numbers and rollout dates in **Design** or **Implementation**, not in `CONTEXT.md`.
