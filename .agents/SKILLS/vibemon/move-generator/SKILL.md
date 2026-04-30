---
name: move-generator
description: >
  Orchestrates creative Vibemon move generation in two phases. Default behavior is
  concept generation and review (no code output, no file edits). Code rendering and
  file writes are allowed only after explicit user approval. Uses provider docstring,
  type quotas, and learnset constraints.
metadata:
  version: 1.3.0
---

# Vibemon Move Generator (Orchestrator-First)

Default behavior is ideation orchestration, not code generation.

## Core Contract

1. **Phase A (default): orchestration only**
   - Produce concepts, never Python.
   - No code fences, no `schema.Move(...)`, no file edits.
2. **Phase B (gated): render + write**
   - Allowed only after exact trigger: `render code now`, `apply phase`, or `commit phase`.
   - Otherwise stay in Phase A.

## Trigger Intent Routing

- `generate moves` / `create Vibemon moves` -> Phase A.
- Phase B requires both explicit trigger and approved concepts.

---

## Phase A — Creative orchestration (default)

### Step A1 — Resolve provider and batch size `N`

- Get provider id (`name`) and `N` unless already provided.
- Pushback:
  - If `N < 50`, recommend `N >= 50`.
  - If `N < k` after type inference, stop until `N >= k` or user narrows types.

### Step A2 — Theme and typing universe

- Read concrete provider docstring: `backend/app/plugins/<provider>/provider.py`.
- Infer `available_types` = docstring-mentioned `VibemonTypeT` + `NORMAL`.
- If ambiguous, ask user to confirm inferred set.
- Sort types in `types.VibemonTypeT` enum order.

### Step A3 — Balance scaffold (still no code)

- Type quotas: `base = N // k`, `rem = N % k`, first `rem` types get +1.
- Level-1 share: choose `L1` minimizing `|L1 / N - 0.7|` (tiebreak upward). This is a **hard target**, not advisory — see Step B2.5 gate.
- Per-type L1 floor: each type's L1 share must land within `±15pp` of the batch L1 ratio. No type may hoard or starve the L1 bucket.
- Non-L1 levels: use `references/move_balance_reference.md`; keep `56-80` sparse, `81-100` trace.
- Secondary-effect budget (damaging moves only): target `~70%` with no rider and `~30%` with riders.
  - Compute per-batch rider budget before ideation using `D = damaging_move_count`.
  - Use `R = round(0.3 * D)` as target rider count (acceptable drift: `R ± 1` for small batches).
  - Treat status moves separately: they always have effects and never count toward the damaging-move rider budget.
- Power-band distribution (damaging moves only): compute per-tier targets from `references/move_balance_reference.md` §3.5.
  - Floor: each tier must reach `≥50%` of its target count.
  - Ceiling: no single tier may hold `>40%` of damaging moves.
  - Capstone rule: at least **one** move at `power ≥120` per batch.
- Priority budget: at most `~7%` of moves in the batch carry elevated priority (`priority ≥1`). Higher tiers (`+2..+7`) follow the sparsity ladder in `references/move_balance_reference.md` §3.6.

### Step A4 — Parallel creative subagents (required)

Run 3 subagents in parallel, then synthesize:
- **Voice**: names + flavor voice.
- **Mechanics**: archetypes + gameplay roles.
- **Theme guard**: fidelity + novelty + anti-cliche.

Hard output format:
- no Python, no code fences, no pseudo-code,
- structured prose records only with:
  `name`, `type`, `role`, `fantasy`, `counterplay`, `approx_power_band`, `power_tier`, `level_band`, `level`, `priority`, `effect_hook`.
- `power_tier` ∈ {`status`, `spam`, `early-stab`, `mid`, `workhorse`, `high`, `signature`} per `references/move_balance_reference.md` §3.5.
- `level` is the numeric `level_requirement` (1–100), not a band.
- `priority` defaults to `0`; non-zero priority must cite §3.6 sparsity bracket.

### Step A5 — Code leakage handling (hard)

If any subagent leaks code:
1. Reject output.
2. Re-run once with stricter no-code constraints.
3. If it leaks again, drop that branch.
Never sanitize leaked code into accepted output.

### Step A6 — Intra-batch anti-repetition checks (required)

Before presenting concepts, rewrite entries that repeat:
- name stems/prefix ladders,
- flavor sentence skeletons,
- mechanic templates with trivial reskins.
Enforce only within the current batch (no cross-run memory required).
- Rider-budget conformance (required):
  - Audit damaging moves and mark each as `clean damage` or `has rider`.
  - If rider count exceeds the Step A3 budget, strip riders from weakest-justified entries first until back in budget.
  - In concept tables, `effect_hook` is allowed to be explicit `none (clean damage)` for damaging moves without riders.

### Step A7 — Human approval gate (required)

Present concise concept table. Require either per-row approval or explicit `approve all`.
No Phase B without this gate.

Before the table, print a **batch summary block** the user can verify at a glance:

```
Batch summary
  N: <total>      L1 count: <X> / <N>      target: round(0.7 * N), tolerance ±5pp
  Damaging: <D>   riders: <R> / <D>        target: round(0.3 * D)
  Power tiers: spam=<a>  early=<b>  mid=<c>  workhorse=<d>  high=<e>  signature=<f>
  Priority elevated (≥1): <p> / <N>        cap: round(0.07 * N)
  Per-type L1 share min/max: <lo>% / <hi>% (must be within ±15pp of batch ratio)
```

A user cannot `approve all` without seeing this block first.

Suggested columns:

| Name | Type | Role | Fantasy | Power Tier | Power Band | Level | Priority | Effect Hook | Status |
|------|------|------|---------|------------|------------|-------|----------|-------------|--------|

---

## Phase B — Render approved concepts to code (explicit opt-in only)

Enter this phase only after:

1. explicit trigger (`render code now` / `apply phase` / `commit phase`), and
2. approved concept list from Phase A.

### Step B1 — Ask write mode before edits

For `backend/app/plugins/<provider>/moves.py`, ask: replace `MOVES`, merge, or cancel.
In merge mode, resolve collisions per move with user input.

### Step B2 — Render rules

- Convert approved concepts into `schema.Move`.
- Use `from app import schema, types` and enum members (no raw strings).
- Enforce `1 <= level_requirement <= 100`.
- Enforce unique `Move.name` in batch and merged pool.
- STATUS moves must use `power=None` and non-`None` effect.
- Expose module-level `MOVES = (...,)`.
- Final output must be fully inlined `schema.Move(...)` entries.
- Never leave helper maps/tables, factory/build functions, loops/comprehensions, or generated assembly in the final `moves.py`.
- Flavor text must be unique per move and thematic to that move's fantasy/effect; do not reuse sentence templates.
- For every move, choose `power`, `accuracy`, `pp`, and `level_requirement` by consulting `references/move_balance_reference.md`.
- Resolve dials in this order: type/theme -> category -> power tier -> accuracy/PP -> level band -> secondary effect chance.
- Enforce damaging-move rider budget from Phase A:
  - Let `D` be damaging moves in the rendered set; target `R = round(0.3 * D)` rider-bearing damaging moves.
  - Keep realized rider count within `R ± 1` (small-batch tolerance), preferring fewer riders when tied.
  - For damaging moves outside the rider budget, render with `effect=None`.
- Enforce power-band distribution from Phase A: realized per-tier counts must respect §3.5 floors and ceiling. Re-tier a concept rather than dropping it from the band.
- Enforce priority budget: realized count of `priority ≥1` moves must be `≤ round(0.07 * N)`. Respect the §3.6 sparsity ladder for `+2..+7`.
- Enforce per-type L1 floor: each type's rendered L1 share within `±15pp` of the batch L1 ratio.
- Quality is non-negotiable: never trade moveset quality for speed, token savings, or mechanical safety.
- Never flatten effect design (for example: blanket `effect.chance=1.0` across most moves) unless the user explicitly requests a "safe baseline only" pass.
- For effect-bearing moves, intentionally distribute reliability (`accuracy`, `pp`, `effect.chance`) so utility texture exists across the batch.
- Do not use "all status + guaranteed on-hit effect" as a default generation pattern.
- If time-constrained, reduce scope (fewer moves) rather than lowering move quality.
- Run `uv run ruff format backend/app/plugins/<provider>/moves.py` after rendering.

### Step B2.5 — Mandatory balance quality gate (BLOCKING)

Every check below is **MUST-PASS**. Run `uv run .agents/SKILLS/vibemon/move-generator/scripts/audit_moves.py <provider>` to verify metrics — the script exits non-zero on any HARD gate fail and prints a `VERDICT: PASS|FAIL` line. On any failure, revise the rendered set and re-run the gate before presenting completion. Do not ship a partially-passing batch.

- **Batch Size (HARD)**: `N <= 100` per generation run to maintain quota accuracy. When auditing a provider whose `MOVES` tuple aggregates several past runs, raise the cap with `--cap` (e.g. `uv run .../audit_moves.py climate --cap 300`); quota gates remain proportional.
- **L1 ratio (HARD)**: `|L1/N - 0.7| ≤ 0.05`. If outside this window, REJECT and rebalance — do not negotiate.
- **Per-type L1 floor (HARD)**: every type's L1 share within `±15pp` of the batch L1 ratio.
- **Level density**: keep `56-80` sparse and `81-100` trace unless explicitly requested otherwise.
- **Power-band distribution (HARD)**: per `references/move_balance_reference.md` §3.5 — every tier ≥50% of target floor, no tier >40% of damaging moves, ≥1 capstone (power ≥120) present.
- **Priority budget (HARD)**: count of moves with `priority ≥1` must be `≤ round(0.07 * N)`; per-tier sparsity caps from §3.6 hold.
- **Sure-Hit budget (HARD)**: count of moves with `accuracy=None` must be `≤ round(0.05 * N)`.
- **Dial sanity**: run anti-pattern checks from `references/move_balance_reference.md` §12.
- **Effect texture**: meaningful variance in effect reliability; no single pattern dominates.
- **Damaging-rider ratio (HARD)**: damaging moves at ~`70%` no rider / `~30%` rider-bearing (within Step B2 tolerance). STATUS moves are exempt from the ratio but should not be used to bypass the "Loaded" feel of a moveset.
- **Type/category fit**: cross-category choices flavor-justified, not accidental.

After all checks pass, print the same batch summary block from Step A7 with realized values for the user to confirm.

### Step B3 — Chat output style

- Do not dump full code unless asked.
- Report path, mode, count, and concise diff summary.

---

## Quality Checklist

- [ ] Default run stayed in Phase A unless explicit Phase B trigger was present
- [ ] Provider docstring read from concrete provider class file
- [ ] `available_types` inferred from docstring + `NORMAL`
- [ ] `N >= k` enforced (or exception documented)
- [ ] Per-type quotas computed with even split + enum-order remainder
- [ ] `L1` chosen by `|L1/N - 0.7|` rule (upward tiebreak), realized within `±5pp` (HARD)
- [ ] Per-type L1 share within `±15pp` of batch ratio (HARD)
- [ ] Non-L1 level bands follow `references/move_balance_reference.md` density guidance
- [ ] Power-band distribution respects §3.5 floors, ceiling, and capstone rule
- [ ] Priority budget: ≤7% elevated priority (`priority ≥1`); §3.6 sparsity respected
- [ ] Approval gate showed batch summary block (Step A7) before user signed off
- [ ] 3 parallel creative subagents were used in Phase A
- [ ] Any code leakage was rejected and re-run policy applied
- [ ] Intra-batch anti-repetition checks passed
- [ ] Manual concept approval occurred before Phase B
- [ ] Phase B edits happened only after explicit trigger and write-mode confirmation
- [ ] Final `moves.py` uses only inlined `schema.Move(...)` entries (no helper maps/builders/generators/comprehensions)
- [ ] Flavor text is unique and move-specific (not templated boilerplate)
- [ ] `power`/`accuracy`/`pp`/`level_requirement` were selected by consulting `references/move_balance_reference.md`
- [ ] Generation did not sacrifice quality for speed or simplicity
- [ ] Effect reliability is intentionally varied (no blanket `chance=1.0` pattern unless explicitly requested)
- [ ] Damaging moves respect rider budget: `~70%` no rider / `~30%` with riders (status moves excluded)
- [ ] Batch passes mandatory balance quality gate (L1 ratio, level density, anti-patterns, effect texture, type/category fit)
- [ ] Ruff format was run on `backend/app/plugins/<provider>/moves.py`

## Reference

- `references/move_balance_reference.md` (single source of truth for balancing and level placement)
- `scripts/audit_moves.py` — gate generated moves data against the Step B2.5 HARD checks; prints A7 batch summary + per-gate `[PASS]/[FAIL]` and exits non-zero on any failure (run with `uv run .agents/SKILLS/vibemon/move-generator/scripts/audit_moves.py [provider]`)
