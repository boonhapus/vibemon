# Development Overrides

Local-only flags for rehearsing flows without production guardrails. These are **not** available when `VIBEMON_ENVIRONMENT=prod`.

Add new entries here whenever a dev bypass is introduced.

## Web UI query parameters

| Route | Query parameter | Effect |
| --- | --- | --- |
| `/hatch` | `bypass-credits=true` | Skip daily generation credit checks when hatching a candidate. Also forwarded to `POST /api/candidates/generate?bypass-credits=true`. |

Examples:

```text
http://localhost:5173/hatch?bypass-credits=true
http://127.0.0.1:5173/hatch?bypass-credits=1
```

Truthy values: `true`, `1`, or an empty value (`?bypass-credits`).

## HTTP API dev flags

| Endpoint | Flag | Effect |
| --- | --- | --- |
| `POST /api/candidates/generate` | `?bypass-credits=true` | Skip daily generation credit reservation and consumption. Honored only when `VIBEMON_ENVIRONMENT` is `dev` or `test`. |
| `POST /api/providers/{id}/prefetch` | JSON body `force_refresh: true` | Bypass upstream HTTP cache for provider prefetch. |

## CLI script flags

See also [SCRIPT_FRONTEND_CONTRACT.md](./SCRIPT_FRONTEND_CONTRACT.md).

| Flag | Scripts | Effect |
| --- | --- | --- |
| `--bypass-credits` | `generate_vibemon.py`, `simulate_adoption.py`, … | Skip trainer generation credit checks. Defaults to enabled on local rehearsal scripts. |
| `--bust-cache` | Scripts that call external providers | Force fresh upstream HTTP responses instead of cached ones. |

## Environment

| Variable | Values | Effect |
| --- | --- | --- |
| `VIBEMON_ENVIRONMENT` | `dev`, `test`, `prod` (default) | `prod` disables web/API dev bypasses such as `bypass-credits`. Also controls secure session cookies. |
