---
name: provider-balance-analysis
description: Rerun and interpret Vibemon provider balance analysis after changes to vibemon/backend/app/providers, vibemon/backend/app/domains/move, vibemon/backend/app/domains/vibemon, vibemon/backend/app/domains/battle, or database persistence shape. Use when assessing dominant or underperforming climate scenarios, provider contract health, generated type/stat/move ecology, or whether climate provider tuning is needed.
---

# Provider Balance Analysis

Use this skill to rerun the self-contained provider balance analyzer bundled in this skill. The analyzer lives in this skill's `scripts/` directory and is independent of repo-local scratch scripts.

## Quick Run

From the repo root:

```powershell
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/provider_analysis.py --battle-rounds 1 --format text --output provider_balance_report.txt
```

For JSON suitable for diffing:

```powershell
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/provider_analysis.py --battle-rounds 1 --format json --output provider_balance_report.json
```

For a fast smoke run:

```powershell
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/provider_analysis.py --scenario-limit 4 --battle-rounds 1 --policies best_damage --format text
```

## What The Script Covers

The bundled analyzer creates synthetic climate payloads and checks:

- provider contract behavior: exposed elements, replay determinism, `synthesize()` purity, persisted provenance columns,
- climate move catalog: type/category/level distribution, effects, status access, priority, and condition usage,
- generated affinities: element frequency, dual-type rate, BST, battle roles, stat spread, move-set quality,
- battle impact: fixed-seed 1v1 simulations using `best_damage`, `stab_first`, `status_aware`, and `random` policies,
- Pokemon benchmark gaps: four-move limit, abilities/items/weather/conditional mechanics, and provider-generated species differences.

The script is offline: it uses synthetic provider payloads and should not call Open-Meteo.

## Interpreting Findings

- Treat `dominant` and `weak` scenarios as investigation leads, not automatic balance bugs.
- Before editing `vibemon/backend/app/providers/climate`, identify whether the cause is provider mapping, move catalog, battle engine behavior, or simulator assumptions.
- A scenario matters most when it is both severe and prevalent. Synthetic edge cases with rare real-world frequency may be acceptable.
- Check whether a result is caused by missing battle mechanics before tuning provider data. Weather moves, first-party scripts, and conditional priority may be intentionally unimplemented or not wired yet.
- Compare reports before and after a tweak using the JSON output. Look for changes in win rates, role concentration, type frequency, STAB counts, and top findings.

## When To Tune Climate

Consider updating `vibemon/backend/app/providers/climate` only if:

- the scenario is likely common in realistic births or too extreme when it occurs,
- the issue remains after accounting for BST, move count, type matchup, and policy choice,
- the root cause is climate-specific: signal thresholds, type scoring, stat signal mapping, intensity, or move assignment.

Prefer battle-system fixes when the finding points to inert mechanics, such as conditional priority not being applied or weather having no battle effect.

## Verification

After changing the skill script, run:

```powershell
uv run --with ruff --with-editable ./vibemon/backend --with sqlalchemy ruff check .agents/skills/vibemon/provider-balance-analysis
uv run .agents/skills/vibemon/provider-balance-analysis/scripts/provider_analysis.py --scenario-limit 4 --battle-rounds 1 --policies best_damage --format json
```

After changing backend balance logic, rerun the full report and keep the old report available long enough to compare.
