# Script Frontend Contract

`vibemon/scripts` is the near-term frontend surface while the API shape is still settling. Frontend and dev tooling should invoke these commands as Python modules from the repository root:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.<command> <args>
```

## Process Contract

- `stdout` is machine-readable JSON for successful commands.
- `stderr` is diagnostics only and must not be parsed as data.
- A zero exit code means the workflow committed successfully.
- A non-zero exit code means no successful result should be consumed.
- `--database-url` accepts any SQLAlchemy async database URL supported by the backend.
- If `--database-url` or `--asset-store-url` is omitted, scripts use `VIBEMON_STORAGE__DATABASE` and `VIBEMON_STORAGE__ASSETS` from repo-root `.env` via `Settings.load()`.
- Scripts create database tables by default for local/dev use. Pass `--no-create-schema` when the frontend owns schema setup.
- Timestamps are ISO-8601. Naive timestamps are treated as UTC; `Z` is accepted.
- UUID arguments are standard UUID strings.

## Commands

Generate a candidate for trainer review:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.generate_candidate --trainer-id <uuid> --latitude <float> --longitude <float>
```

Useful optional flags: `--timestamp <iso>`, `--nickname <text>`, `--core-identity <text>`, `--bypass-credits`, `--christen`.

Generate wild supply:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.generate_wild_supply --latitude <float> --longitude <float>
```

Useful optional flags: `--timestamp <iso>`, `--nickname <text>`, `--core-identity <text>`, `--christen`.

Adopt a pending candidate:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.adopt_candidate --trainer-id <uuid> --vibemon-id <uuid>
```

Useful optional flags: `--release-vibemon-id <uuid>`, `--manifest`.

Reject a pending candidate:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.reject_candidate --trainer-id <uuid> --vibemon-id <uuid>
```

Release an owned Vibemon:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.release_vibemon --trainer-id <uuid> --vibemon-id <uuid>
```

Pick a wild encounter:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.pick_wild_encounter --trainer-id <uuid> --latitude <float> --longitude <float> --party-strength <float>
```

Useful optional flag: `--desired-supply <int>`.

Christen an existing born Vibemon:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.christen_vibemon --vibemon-id <uuid>
```

Manifest an existing christened Vibemon:

```powershell
uv run --project vibemon/backend python -m vibemon.scripts.manifest_vibemon --vibemon-id <uuid>
```

## Current Boundaries

The exposed scripts cover the product-facing generation, adoption, release, encounter-pick, christen, and manifest flows. Maintenance workflows remain app-only until a frontend or dev tool needs them: wild encounter outcome recording, wild expiration, review/hold timeout resolution, and expired asset pruning.
