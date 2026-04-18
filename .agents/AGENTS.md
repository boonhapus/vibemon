# AGENTS.md

## Frontend: Svelte 5
- `$state()`, `$derived()`, `$effect()` — runes only
- `$props()` — no `export let`
- Snippets replace slots
- `Tween`, `Spring` from `svelte/motion`

## Backend: Python 3.14
- Prefer `asyncio.TaskGroup`, `asyncio.timeout`, `except*`
- No blocking — all async I/O
- `from __future__ import annotations` → PEP 695 style
- Use `match/case` for pattern matching

## Stack
- SvelteKit 2 + adapter-static
- Litestar 2.x
- pnpm (Node), uv (Python)