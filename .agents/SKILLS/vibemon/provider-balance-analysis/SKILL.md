---
name: provider-balance-analysis
description: Audit Vibemon provider move catalogs (data/moves.json) against move-generator Step B2.5 balance gates. Use after editing app/providers/*/data/moves.json or when validating a new provider move batch.
---

# Provider Move Balance

Audit any provider move catalog under `vibemon/backend/app/providers/<name>/data/moves.json`.

Providers are **discovered automatically** when `app/providers/<name>/data/moves.json` exists. No registry to update when adding a provider.

## Run

```powershell
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider biome
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider climate
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider music
```

Accumulated catalogs (N > 120) default to `--cap 300`:

```powershell
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider biome --cap 300
```

Exit code is non-zero when any hard gate fails. Look for `VERDICT: PASS|FAIL`.

## Gates (Step B2.5)

- Batch size, L1 ratio, per-type L1 share
- Power-band quotas (spam through signature), capstone
- Damaging rider budget, L1 damaging power caps
- Priority budget and sparsity ladder
- Sure-hit budget, early accuracy/evasion guard
- §12 anti-patterns

Detail tables: type distribution, level bands, category mix, power tiers, per-type riders, effect texture.

## Interpreting failures

- **Power-band / early-stab ceiling** — catalog skewed low; add mid/workhorse moves or relabel power tiers.
- **Rider budget** — too few or too many damaging moves with secondary effects vs ~30% target.
- **Anti-patterns** — individual moves break power/accuracy/PP/status tradeoff rules; fix the move, not the gate.

Provider birth logic, stats, and battle outcomes are out of scope here — use existing battle simulation workflows for that.

## Adding a provider

1. Add `app/providers/<name>/data/moves.json`.
2. Run `uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider <name>`.

`provider.py` is not required for discovery; only `data/moves.json` is scanned.

## Verification

```powershell
uv run --with ruff --with-editable ./vibemon/backend ruff check .agents/skills/vibemon/provider-balance-analysis
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/audit_moves.py --provider climate --cap 300
```
