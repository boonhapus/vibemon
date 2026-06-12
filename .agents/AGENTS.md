# AGENTS.md

This file tells coding agents what the vibemon project uses and what to follow.

**Rules** = you must follow these.  
**Conventions** = you should follow these unless a ticket says otherwise.

---

## Stack (what the project uses)

**Frontend**

- SvelteKit 2
- Static adapter
- pnpm
- Svelte 5

**Backend**

- Litestar 2.x
- Python 3.14
- uv (use this to run Python commands)

**Python libraries (see also `development/python-conventions` skill)**

- HTTP client: niquests
- Data models and parsing: Pydantic
- Logs: structlog

More Python import rules: `.agents/SKILLS/development/python-conventions/SKILL.md`

---

## Rules (must follow)

### Svelte 5 frontend

1. Use runes: `$state()`, `$derived()`, `$effect()`.
2. Use `$props()` for inputs. Do not use `export let`.
3. Use snippets. Do not use old slots.

### Python backend

1. Use async code for I/O. Do not block the event loop on request paths.
2. Target Python 3.14.
3. Do not add `from __future__ import annotations`.

### Backend module roles: `const.py`, `types.py`, `schema.py`, `models.py`

Use these names consistently at the top level and inside subpackages. For
example, `app.storage.database.types` should mean the same kind of thing as
`app.core.types`, but scoped to storage.

**Put in `const.py`**

- Fixed values, thresholds, tunables, and lookup tables.
- Static mappings between known units, such as enum-to-enum or enum-to-MIME-type maps.
- No I/O, no generated runtime state, and no business workflows.

**Put in `types.py`**

- Units of meaning: enums, constrained vocabularies, type aliases, protocols, and `TypedDict`s.
- Names that describe what a value is, not an object carrying live state.
- No Pydantic data objects, SQLAlchemy models, or imports from `schema.py` / `models.py`.

**Put in `schema.py`**

- Pydantic data objects used by the app at runtime: Vibemon, moves, battle state, logs, API payload shapes, and small serializable records.
- Validation, serialization shape, and domain behavior that belongs to those data objects.
- No SQLAlchemy sessions, queries, commits, or table declarations.

**Put in `models.py`**

- SQLAlchemy ORM table declarations, relationships, constraints, and database column types.
- Persistence shape only. Keep generation, API orchestration, and object-store writes out of ORM models.
- Mapping between Pydantic schema objects and ORM models belongs in a caller/service/helper module, not in `models.py` by default.

**Import direction**

- `types.py` is low-level and must not import `schema.py` or `models.py`.
- `const.py` may import `types.py` for typed lookup keys, but must not import `schema.py` or `models.py`.
- `schema.py` may import `types.py` and `const.py`.
- `models.py` should stay independent of Pydantic `schema.py`; use external mapper/helper code when conversion is needed.

---

## Conventions (should follow)

### Frontend

- For **state-driven** motion (values that follow reactive state), use `Tween` and `Spring` from `svelte/motion`. Prefer `prefersReducedMotion` from the same module over manual `matchMedia` checks.
- For **fixed choreographies** (multi-element sequences, screen wipes, battle beats), use CSS `@keyframes` with shared `--anim-*` tokens from `vibemon/frontend/src/lib/ui/tokens.css` and `steps()` timing per `docs/development/DESIGN.md`.
- For simple enter/leave on mount/unmount, use `transition:` from `svelte/transition`.

### Backend

- Run tools with `uv run`, not `python`. Example: `uv run ruff check .`
- When it helps readability, use `asyncio.TaskGroup`, `asyncio.timeout`, and `except*`.
- When it helps readability, use `match` / `case` and `:=` (assign inside an expression).

### Before you commit

- Run `ruff check .` and `ruff format .` on the backend code.

---

## Skills (extra playbooks)
**On this machine (not in the repo folder)**

- Folder: `~/.agents/skills/`
- `caveman` — ultra-compressed communication mode
- `caveman-commit` — ultra-compressed commit messages
- `grill-with-docs` — stress-test plans against project docs
- `karpathy-guidelines` — reduce LLM coding mistakes
- `to-prd` — turn conversation into PRD

**Inside this repo**

- Path: `.agents/SKILLS/`
- `development/python-conventions` — Python imports and libs
- `development/svelte-code-writer` — Svelte 5 docs lookup and component analysis (use for `.svelte` edits)
- `development/svelte-core-bestpractices` — Svelte 5 reactivity and patterns
- `vibemon/move-generator` — provider-driven move generation playbook (also read `vibemon/move-generator/references/move_balance_reference.md`)
- `vibemon/provider-balance-analysis` — audit provider move catalogs
- `vibemon/audio-production-pipeline` — stage, loop-test, and export music cues

---

## Design context

Before designing or building UI, read:

- **[docs/development/DESIGN.md](../docs/development/DESIGN.md)** — visual spec: battle animation, audio, typography, layout
- **[docs/development/COLORS.md](../docs/development/COLORS.md)** — locked palette (canonical for `vibemon/frontend/src/lib/ui/tokens.css`)
- **[docs/development/plans/trainer-setup-storyboard.md](../docs/development/plans/trainer-setup-storyboard.md)** — first-run trainer setup UX wireframes

Domain vocabulary: [docs/development/CONTEXT.md](../docs/development/CONTEXT.md).
