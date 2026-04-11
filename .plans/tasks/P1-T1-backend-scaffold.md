# P1-T1 — Backend Scaffold & Health Endpoint

**Phase:** 1 — Core Pipeline
**Dependencies:** None (start here)
**Depends on this:** P1-T2, P1-T3, P1-T4, P1-T5, P1-T6, P1-T7

---

## Objective

Stand up a working Litestar application with project structure, dependency management, and a health endpoint that proves the server runs.

## Tasks

1. **Initialise the Python project with `uv`**
   - Create `backend/` directory
   - `uv init` and add dependencies: `litestar`, `uvicorn`, `attrs`, `cattrs`, `structlog`, `niquests`
   - Create a `backend/app/` package with `__init__.py`

2. **Configure structlog**
   - Create `backend/app/logging.py`
   - Set up JSON-formatted structured logging with request-id context
   - Configure at app startup

3. **Create the Litestar application entry point**
   - `backend/app/main.py` — instantiate `Litestar(route_handlers=[...])`
   - Add CORS middleware allowing the frontend origin (`http://localhost:5173` for dev)

4. **Implement `GET /api/v1/health`**
   - `backend/app/routes/health.py`
   - Return `{"status": "ok", "providers": {}}` (provider checks come later)
   - Wire into the app's route handlers

5. **Create a dev run script**
   - `backend/run.py` or a `Makefile` target that runs `uvicorn app.main:app --reload`

## Acceptance Criteria

- `uv run uvicorn app.main:app` starts without error
- `GET http://localhost:8000/api/v1/health` returns `200` with `{"status": "ok"}`
- structlog outputs JSON to stdout on each request

## Files Created

```
backend/
  pyproject.toml
  app/
    __init__.py
    main.py
    logging.py
    routes/
      __init__.py
      health.py
```
