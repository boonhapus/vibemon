# Scripts

These scripts are a rehearsal surface for Vibemon experiences.

They are not a second application layer and they should not compete with
`app.workflows`. Durable product behavior belongs in `app.workflows` and the
domain modules underneath it. Scripts are allowed to orchestrate those workflows
in opinionated ways so we can manually exercise representative slices of the UX
before the frontend exists.

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
- Prefer useful local defaults: generated SQLite database, local asset store,
  auto-created schema, random coordinates when location is not the point of the
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
- Use `--name` for trainer display names, `--nickname` for Vibemon nicknames,
  and `--idea` for creative generation nudges.
- Keep `--database-url`, `--asset-store-url`, and credit bypass controls in the
  advanced group.

## Current Scripts

The current one-workflow scripts can be reduced toward a smaller set of
experience-oriented orchestrators:

- `generate_vibemon.py`: create a Vibemon at a requested lifecycle or review
  stage, such as born, christened, manifested, candidate, wild, or owned.
- `simulate_adoption.py`: rehearse trainer review behavior, including candidate
  generation, adoption, rejection, party-full release swaps, and optional
  manifestation.
- `simulate_wild_encounter.py`: rehearse searching the wild, selecting an
  encounter, optionally battling, and recording the encounter outcome.
- `simulate_battle.py`: rehearse a pure battle between two selected or generated
  Vibemon without requiring the full encounter/adoption flow.
- `rebalance_vibemon.py`: replay existing Vibemon from persisted birth snapshots
  through the current provider balance logic and optionally update their derived
  typing, stats, and active moves.

The goal is for these scripts to describe the behavior we expect future UI flows
to drive, while the workflows remain the canonical place for persisted behavior.

## Generate Vibemon CLI Shape

`generate_vibemon.py` is intentionally beginner-first. The common path is:

```powershell
uv run python scripts/generate_vibemon.py --stage manifested --nickname Mochi
```

The visible options describe rehearsal intent:

- `--stage`: the UX state to create, such as `born`, `manifested`, `candidate`,
  `wild`, or `owned`.
- `--lifecycle`: how visually complete candidate, wild, or owned Vibemon should
  be: `born`, `christened`, or `manifested`.
- `--trainer` and `--name`: trainer context for candidate and owned stages.
- `--location` and `--born-at`: deterministic birth seed inputs when randomness
  is not useful.
- `--nickname` and `--idea`: creative nudges for the generated Vibemon.

Advanced plumbing appears in its own help section: `--database-url`,
`--asset-store-url`, and `--bypass-credits`.

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
- `--nickname` and `--idea`: creative nudges for the generated candidate.

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

## Rebalance Vibemon CLI Shape

`rebalance_vibemon.py` previews changes by default, so the fastest inspection
path is:

```powershell
uv run python scripts/rebalance_vibemon.py --limit 20
```

The visible options describe rebalance intent:

- `--vibemon`: replay one existing Vibemon by ID; omitted selects persisted rows.
- `--limit`: cap how many persisted Vibemon are replayed during exploratory
  checks.
- `--apply`: persist the replayed typing, stats, and active moves; omitted runs a
  dry run.
- `--examples`: control how many changed examples appear in the compact JSON
  output.
- `--detail`: use `summary` for compact counts/examples or `full` for complete
  before/after identity and active move definitions.
- `--include-unchanged`: include unchanged rows in full-detail reports.

Advanced plumbing appears in its own help section: `--database-url` and
`--output`.

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
