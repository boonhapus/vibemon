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

**Python libraries (see also `python-conventions` skill)**

- HTTP client: niquests
- Data classes: attrs and cattrs
- Logs: structlog

More Python import rules: `.agents/SKILLS/python-conventions/SKILL.md`

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

### Where code goes: `types.py` vs `schema.py`

**Put in `types.py`**

- Enums (example: move category, status names)
- Type aliases (example: trainer id type)

**Put in `schema.py`**

- Game objects which need to hold data (example: vibemon, trainer, battle state, turn logs)

**Import direction**

- `schema` may import `types`. OK.
- Game engine may import `schema` and `types`. OK.
- `types` must not import `schema`. Not OK.

---

## Conventions (should follow)

### Frontend

- For motion, use `Tween` and `Spring` from `svelte/motion`.

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
- Examples: caveman, caveman-commit, nelson, karpathy-guidelines

**Inside this repo**

- Path: `.agents/SKILLS/`
- `python-conventions` — Python imports and libs
- `wrangle-commits` — how to split commits
