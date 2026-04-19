# AGENTS.md

## Tech Stack
- SvelteKit 2 + adapter-static
- Litestar 2.x
- pnpm (Node), uv (Python)

**Frontend: Svelte 5**
- `$state()`, `$derived()`, `$effect()` — runes only
- `$props()` — no `export let`
- Snippets replace slots
- `Tween`, `Spring` from `svelte/motion`

**Backend: Python 3.14**
- Use `uv run` instead of `python` or `python3`
- Prefer `asyncio.TaskGroup`, `asyncio.timeout`, `except*`
- No blocking — all async I/O
- Use the `match` statement instead of `if/elif/else` if it would aid in readability
- Use the assignment operator `:=` if it would aid in readability
- Do not use `from __future__ import annotations` for forward references, 3.14 has deferred evaluation
- Use `match/case` for pattern matching
- Run `ruff check .` and `ruff format .` before commit.


## Code rules

**Karpathy guidelines apply.** Source: `tickets/` files reference these. In brief:
- No speculative abstractions. Build what the ticket says, nothing more.
- Every changed line must trace to a ticket.
- Surface assumptions explicitly — don't silently pick an interpretation.
- Define a verifiable done-when before writing code, not after.

## Skills
- python-conventions: Python conventions for this project.
