---
name: python-asyncio
description: Asyncio patterns for Python 3.12+—structured concurrency, cancellation, timeouts, and exception groups—without blocking the event loop.
metadata:
  version: 1.1.0
  language: python
  tags: [asyncio, python-3.12, taskgroups, contextvars, exception-groups]
---

# Python 3.12+ asyncio (agents & services)

**Requires Python ≥3.12** (TaskGroup, `asyncio.timeout`, `except*` / PEP 654).

Priorities: **structured concurrency**, **no blocking on the event loop**, **clear failure modes** (strict vs partial success).

## Critical constraints

- **Blocking the loop:** Avoid `time.sleep()`, synchronous HTTP (`requests`, …), and blocking DB drivers (e.g. default `sqlite3`) unless work runs in `asyncio.to_thread()` or a native async API. One block stalls every concurrent task on that loop.
- **Session / request context:** Do not stash per-request data on globals or shared mutable class fields. Use **`contextvars.ContextVar`** so concurrent runs cannot leak into each other.
- **`ContextVar.get()`:** Prefer a default (`get(None)` + guard, or `ContextVar(..., default=...)`) so nested code never raises `LookupError` if the entry point forgot to set the var.

## Parallel work: choose the failure model

| Goal | Pattern |
|------|---------|
| **Strict:** every child must succeed; abort the whole step if any fails; nested scopes stay well-defined | **`asyncio.TaskGroup`** |
| **Partial success:** run N things; keep successes; ignore or log individual failures (e.g. optional providers) | **`asyncio.gather(..., return_exceptions=True)`** and inspect results, **or** `TaskGroup` with each child wrapping its own `try`/`except` so nothing unhandled escapes |

**`asyncio.gather` facts:** With default `return_exceptions=False`, the first raised exception is propagated and **remaining awaitables are cancelled**—not “zombie” siblings. With **`return_exceptions=True`**, exceptions come back as values and **other tasks are not cancelled**; that matches “best effort” fan-out but needs explicit handling so nothing is forgotten.

**`TaskGroup` and exceptions:** If multiple children fail, exiting the group can surface an **`ExceptionGroup`**. `ExceptionGroup` is a subclass of **`Exception`**, so `except Exception` **does** catch it; use **`except* SomeError`** when you need **per-sub-exception** handling, or unwrap `eg.exceptions` manually.

```python
import asyncio

async def strict_orchestration(tool_runs: list):
    """All tools must complete without raising."""
    try:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(run()) for run in tool_runs]
    except* Exception as eg:
        for exc in eg.exceptions:
            handle_tool_error(exc)
        raise
    return [t.result() for t in tasks]


async def best_effort_gather(awaitables):
    """Keep successes; tolerate per-item failure."""
    outcomes = await asyncio.gather(*awaitables, return_exceptions=True)
    ok, errs = [], []
    for item in outcomes:
        (errs if isinstance(item, BaseException) else ok).append(item)
    return ok, errs
```

## Resilience

- **`asyncio.timeout(delay)`:** Bound every external call (LLM, HTTP, tool).
- **Retries:** e.g. `tenacity` with async-aware retry for transient network errors.
- **CPU / blocking libs:** `asyncio.to_thread(func, *args)`.

## Checklist

- [ ] No blocking I/O on the event loop (`await` async APIs or offload).
- [ ] Parallel work has an explicit policy: **strict** (`TaskGroup` / fail-fast) vs **best-effort** (`gather(return_exceptions=True)` or isolated `try` per child).
- [ ] No orphaned tasks: everything is awaited, cancelled on shutdown, or owned by a `TaskGroup` / explicit task set.
- [ ] Timeouts on outward calls; `CancelledError` handled where shutdown matters.
- [ ] Tool/request payloads validated with the project stack (e.g. **attrs** + **cattrs**, Pydantic, msgspec).

## Optional stack notes

| Area | Common choice | Note |
|------|----------------|------|
| HTTP | `httpx`, **Niquests**, etc. | Must be async or offloaded. |
| DB | SQLAlchemy async, etc. | Match driver to async loop. |
| Retries | `tenacity` | Use async-compatible patterns. |
| **uvloop** | Faster loop on **Unix** | Not supported on **Windows**; stay on default loop there. |

## Agent-shaped workflow (compact)

1. Parse intent → list of tools / steps.
2. Set `ContextVar`s at the request boundary.
3. Run parallel segment with the right pattern (**TaskGroup** vs **`gather(..., return_exceptions=True)`**), each call under **`asyncio.timeout`**.
4. On structured failures, use **`except*`** or normalized error payloads for retry / user messaging.
5. Prefer **`AsyncGenerator`** for streaming partial results when useful.
