# Scripts

These scripts are a rehearsal surface for Vibemon experiences.

They are not a second application layer and they should not compete with
`app.workflows`. Durable product behavior belongs in `app.workflows` and the
domain modules underneath it. Scripts are allowed to orchestrate those workflows
in opinionated ways so we can manually exercise representative slices of the UX
before the frontend exists.

## Dev stack

Run backend (Litestar) and frontend (Vite) together:

```powershell
cd vibemon/backend
uv run dev
```

From repo root:

```powershell
uv run --project vibemon/backend dev
```

Options: `--backend-host`, `--backend-port` (default `127.0.0.1:8000`). Requires `pnpm` on `PATH` and repo-root `.env`. The backend reload watcher only monitors `app/` (not `scripts/`) and logs through structlog at ERROR+.

## Patterns And Philosophy

These scripts should stay small, semantic, and experience-oriented.

- Name scripts after user-facing rehearsal experiences, not individual workflow
  functions. Prefer `simulate_wild_encounter.py` over a pile of one-command
  wrappers around `pick_wild_encounter`, `record_wild_encounter_outcome`, and
  related calls.
- Keep durable product behavior in `app.workflows` and the domain modules.
  Scripts may compose workflows in opinionated ways, but they should not become
  a parallel application layer.
- Put shared command-line plumbing in `_common.py`: session scope, seed parsing,
  local asset setup, loading helpers, battle simulation helpers, and JSON
  dumping.
- Require repo-root `.env` for storage URLs and secrets. Scripts call `_common.load_script_settings()` at startup.
- Auto-create schema on first script run, use random coordinates when location is not the point of the
  rehearsal, and deterministic seeds for battle-heavy flows.
- Emit compact JSON with the IDs and state needed for the next manual step.

CLI interfaces should be beginner-first:

- Use `cyclopts.App` with examples in the app help text.
- Define `COMMON_OPTIONS` and `ADVANCED_OPTIONS`; keep story/rehearsal choices in
  common options and infrastructure knobs in advanced options.
- Use intent names rather than storage names: `--trainer`, `--hero`,
  `--release`, `--location`, `--born-at`, `--searched-at`, `--turns`, and
  `--seed`.
- For optional entity selectors, omission should trigger the script's default:
  usually generated context or, for battle combatants, a random persisted
  database row.
- Avoid aliases unless there is an explicit compatibility reason. When a script
  interface is being cleaned up, prefer one clear public flag.
- Prefer one `--location latitude,longitude` option over separate latitude and
  longitude flags.
- Use `--name` for trainer display names and `--nickname` for Vibemon nicknames.
- Keep `--database-url`, `--asset-store-url`, and credit bypass controls in the
  advanced group.

## Current Scripts

Integration rehearsal and database tooling:

**Database**

- `init_db.py`: create all tables from SQLAlchemy models (idempotent on a fresh DB).
- `db_shell.py`: list tables, run ad-hoc SQL, or open an interactive shell against
  the configured database.

**UX rehearsal**

- `generate_vibemon.py`: create a Vibemon at a requested asset form and optional
  UX stage (`candidate`, `wild`, or `owned`).
- `simulate_adoption.py`: rehearse trainer review behavior, including candidate
  generation, adoption, rejection, crew-full release swaps, and optional
  manifestation.
- `simulate_wild_encounter.py`: rehearse searching the wild, selecting an
  encounter, optionally battling, and recording the encounter outcome.
- `simulate_battle.py`: rehearse a pure battle between two selected or generated
  Vibemon without requiring the full encounter/adoption flow.
- `generate_static_assets.py`: regenerate hand-authored static PNGs from
  `vibemon/frontend/asset-prompts/game/*.mdc`. Pass an asset key (prompt file stem,
  e.g. `vibe-deck`) to render sprite + icon together; omit the key to render all
  non-approved records. Sprites always run before their reference-linked gear HUD icons in the same pass (or use
  `--icons-only` to regen icons against existing sprites). Sprites and gear HUD icons use solved chroma-key mattes
  and trainer-style matte removal — never white backgrounds.
  Outputs default to `<repo>/.generated/assets/` for comparison before copying into `frontend/static/game/`.
- `generate_static_assets.py derive-poses`: classify canonical `{gear}.png` sprites with
  `sprite-facing.mdc`, then write `{gear}-left.png` and `{gear}-right.png` by mirroring — no image gen.
- `manifest_vibemon.py`: generate sprite sheets and pose assets for christened
  Vibemon that are not yet manifested (run after bulk adoption or reference fixes).
  Use `--reprocess` to re-chroma reference and pose PNGs from stored blobs without GenAI
  (fixes opaque backgrounds on already-manifested rows).
- `link_lastfm.py`: store a trainer Last.fm session for local music birth
  rehearsal, or print the browser web-auth URL.

The goal is for these scripts to describe the behavior we expect future UI flows
to drive, while the workflows remain the canonical place for persisted behavior.

## Database setup

Storage URLs are required in repo-root `.env` under `VIBEMON_STORAGE__*` (see `.env.example`).
`Settings.load()` fails if any are missing.

Copy `.env.example` to `.env`, set all values, then initialize schema and catalog defaults (canonical style-bible trainer reference in monstore):

```powershell
cd vibemon/backend
uv run python scripts/init_db.py
```

`init_db.py` creates tables, then seeds trainer `00000000-0000-0000-0000-000000000000` with the shipped style-bible `trainer.png` at `sprite/reference-raw.png` and snapped `trainer@128.png` at `sprite/reference.png` in monstore.

**Postgres (local via Docker)**

```powershell
cd deploy/postgres
docker compose up -d
```

Set in repo-root `.env`:

```powershell
VIBEMON_STORAGE__DATABASE=postgresql+asyncpg://vibemon:vibemon@127.0.0.1:5432/vibemon
```

Then re-run `init_db.py`.

Pre-1.0 schema changes: drop and recreate the database, re-run `init_db.py`, then reseed.
To preserve SQLite data during a one-off move to Postgres, use [pgloader](https://pgloader.io/).

**Tests** use the same URL as `Settings.load().storage.database`. Override the test
database with `VIBEMON_TEST_DATABASE_URL`, or point `VIBEMON_STORAGE__DATABASE` at
Postgres. When Docker is available, testcontainers Postgres is used automatically.

## Generate Vibemon CLI Shape

`generate_vibemon.py` is intentionally beginner-first. The common path is:

```powershell
uv run python scripts/generate_vibemon.py --form manifested --nickname Mochi
```

The visible options are grouped by intent:

**Common** — rehearsal flow and identity:

- `--form`: asset completeness — `born`, `christened`, or `manifested`.
- `--stage`: optional UX destination — `candidate`, `wild`, or `owned`. Omit for a
  plain birth.
- `--trainer` and `--name`: trainer context for candidate and owned stages.
- `--nickname`: optional Vibemon nickname.
- `--affinity-only`: print provider affinities and the merged birth preview without
  persisting a Vibemon.

**Seed** — birth seed inputs:

- `--location` and `--born-at`: deterministic coordinates and timestamp.
- `--provider`: birth providers to include (`climate`, `biome`, `music`); repeat
  the flag to combine them. Default is climate and biome.

**Output**:

- `--count`: how many Vibemon to create.
- `--output`: `json` or `table` (table when `--count > 1`).

Advanced plumbing appears in its own help section: `--database-url`,
`--asset-store-url`, and `--bypass-credits`.

Music birth examples:

```powershell
uv run python scripts/link_lastfm.py --trainer <uuid>
uv run python scripts/generate_vibemon.py --provider music --trainer <uuid> --affinity-only
uv run python scripts/generate_vibemon.py --provider climate --provider biome --provider music --trainer <uuid> --stage candidate
```

When a script uses external providers, add `--bust-cache` to force fresh HTTP
provider responses while still writing them back to Redis or SQLite cache. The
same behavior is available process-wide with `VIBEMON_BUST_CACHE=1`.

## Simulate Adoption CLI Shape

`simulate_adoption.py` defaults to creating and adopting one candidate:

```powershell
uv run python scripts/simulate_adoption.py
```

The visible options describe candidate review intent:

- `--action`: whether to `adopt` or `reject` the generated candidate.
- `--trainer`, `--name`, and `--release`: trainer context and an optional
  release target when adoption needs room.
- `--lifecycle`: how visually complete the candidate should be before
  resolution.
- `--location` and `--born-at`: deterministic birth seed inputs when randomness
  is not useful.
- `--nickname`: optional candidate nickname.

Advanced plumbing appears in its own help section: `--database-url`,
`--asset-store-url`, and `--bypass-credits`.

## Simulate Wild Encounter CLI Shape

`simulate_wild_encounter.py` defaults to generating trainer context, wild
supply, and resolving the selected encounter with an automated battle:

```powershell
uv run python scripts/simulate_wild_encounter.py
```

The visible options describe encounter intent:

- `--resolution`: resolve by `auto-battle`, `run`, `defeat`, or `win-no-adopt`.
- `--trainer`, `--name`, and `--hero`: trainer context and an optional existing
  hero Vibemon.
- `--location` and `--searched-at`: deterministic search seed inputs when
  randomness is not useful.
- `--generate` and `--supply`: wild supply controls before encounter selection.
- `--turns` and `--seed`: deterministic battle controls for automated battle
  resolution.

Advanced plumbing appears in its own help section: `--database-url` and
`--asset-store-url`.

## Simulate Battle CLI Shape

`simulate_battle.py` defaults to two random persisted combatants, so the fastest
rehearsal path is:

```powershell
uv run python scripts/simulate_battle.py
```

The visible options describe battle intent:

- `--vibemon-a` and `--vibemon-b`: existing combatant IDs to load; omitted sides
  are randomly selected from the database.
- `--trainer-a`, `--trainer-b`, `--name-a`, and `--name-b`: trainer context for
  the simulated sides.
- `--seed`: deterministic battle rolls for repeated runs.
- `--move-policy`: automated move selection strategy. Available values are
  `first_available`, `best_damage`, `stab_first`, `status_aware`, and `random`.

Advanced plumbing appears in its own help section: `--database-url` and
`--asset-store-url`.
