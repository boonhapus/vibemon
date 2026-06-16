# Vibemon XP & Evolution

| | |
| --- | --- |
| **Status** | Designed |
| **Priority** | High |
| **Complexity** | Medium |
| **Area** | Meta-Progression |
| **Related** | [mon-event-history.md](mon-event-history.md), [vibe-gold-economy.md](vibe-gold-economy.md), [achievement-system.md](achievement-system.md), [alumni-roster.md](alumni-roster.md), [background-wild-simulation.md](background-wild-simulation.md) |

## Summary

Vibemon gain experience (XP) through battle, advancing in `level` (cap 100). Crossing growth-rate-gated level milestones promotes a mon's `evo_stage` up its evolution line, recomputing its base stats to the new stage's BST target and unlocking moves. The whole system reuses fields that already exist on the entity (`xp`, `level`, `evo_stage`, `evo_seed`) — it adds progression *motion*, not new state axes.

## Problem

Battle wins feel isolated. `xp`/`level`/`evo_stage` exist on the entity but nothing ever moves them: mons are born at `level=1`, `evo_stage=BASE`, and stay there. There is no experience curve, no growth arc, and no payoff for sustained play.

## Concept

One scalar — `level` — drives everything. XP earned from battles raises `level`; `level` milestones promote `evo_stage` (capped by the mon's birth-assigned `evo_seed`); promotion rescales base stats and gates move learning. There is **no separate tier ladder** — a mon's progression "tier" is purely a function of `level` and `evo_seed`.

### What this replaces

The earlier draft proposed a parallel Novice/Adept/Expert/Master tier ladder with flat +10/20/30% stat bonuses. Both are **dropped**: they duplicated mechanics the codebase already has. `level` + `evo_stage` is the progression; `apply_evo_seed_bst_bias` already delivers a per-stage BST jump that *is* the stat reward.

## Design

### Progression axes (all pre-existing fields)

- **`level`** — universal scalar, 1–100. Drives stat scaling (`base_stat_level_scaling`) and every milestone.
- **`evo_seed`** (born) — the evolution *line*: its stage count, per-stage BST targets (`BST_SCALING_MATRIX`), and ceiling. A `BASE`-seed mon never evolves; a `STAGE_3`/`PSEUDO_LEGENDARY`-seed mon climbs through 3 stages.
- **`evo_stage`** — current rung on the line, born at `BASE`, climbs toward the `evo_seed` ceiling.
- **growth rate** (new, born) — see below; sets maturation pace.

Tier = `f(level, evo_seed)`. Not stored separately. (Resolves the old "is level separate from tier" open question: no — tier is derived.)

### Birth: weighted evo_seed + growth rate

Today `evo_seed` is a pure random roll (`EvolutionStageT.random_seed`). Replace with a **weighted roll** so populations steer where we want semantically:

- `intensity` drives rarity.
- High-intensity outcomes are rare; `evo_seed = BASE` (Evo-Seed-1, high BST skew) is also rare.
- Pseudo-legendary retains its 3-stage requirement.

**Growth rate** is a second weighted roll persisted at birth, modelling biological maturity (bugs mature fast, mammals/birds medium, dragons slow):

- `evo_seed` and dominant element **bias the distribution** (the semantic knobs).
- **Entropy** spreads individuals within the biased distribution — growth rate is not fully deterministic.
- Bucketed into named growth groups (Fast / Medium / Slow / …), stored as one column so the XP curve stays stable across element-table retuning.

### XP award

Per fainted opponent, per round (not just end-of-battle):

```
xp = round(BASE_YIELD * opp.level * evo_seed_weight[opp] / DIVISOR)
xp *= TRAINER_KILL_BOOST   # if the defeated mon was trainer-owned
```

- The mon that scored the faint takes the **full share**.
- The remaining **participation share is split among non-fainters that appeared** in the battle.
- The engine is **disposition-agnostic**: wild mons earn XP the same way (e.g. a wild mon fainting a trainer's mon in an encounter). Wild-vs-wild *would* award identically once a background sim exists — see [background-wild-simulation.md](background-wild-simulation.md); not built here.

### XP curve & evolution milestones

- Cumulative **cubic** curve: `xp_to_reach(level) = round(GROWTH_COEFF * level**3)`, where `GROWTH_COEFF` is set by the mon's **growth rate** (fast maturers need less total XP per level).
- `evo_stage` promotes at **growth-rate-gated level milestones**, capped at the `evo_seed` ceiling. Faster growth → earlier milestones; pseudo-legendary milestones land latest. `BASE`-seed mons have no milestones.

### Evolution stat effect

On promotion, **recompute and persist** `identity.base`:

```
apply_evo_seed_bst_bias(stats, evo_seed=evo_seed, evo_stage=new_stage)
```

This rescales the birth stat spread up to the new stage's BST target — a real, legible BST jump (e.g. a STAGE_3 line: 280 → 410 → 530). Snapshot replay (`rebalance`) must replay at the mon's current `evo_stage`. There is **no** separate +% multiplier.

### Move learning

- Moves are learned on **level-up** when `level >= Move.level_requirement`.
- Source pool is the **full providers move pool**, regenerated from `BirthSnapshot` (via the existing `lineage`/`regenerate` path) — *not* only the 2–3 moves selected at birth.
- Evolution co-occurs on level-up, so stage-up and move-learning resolve together.
- With 4 slots full, offer-and-replace (`move_learned` kept/rejected, `move_forgotten`); rejected offers are still recorded.

### Cancel evolution

- **Owned mons only.** Wild mons (background) auto-evolve — no one to prompt.
- **Synchronous post-battle evo screen**: a completed battle resolves XP → levels → then presents eligible owned mons for accept / cancel.
- A decline is "not now": it **re-offers at each subsequent level-up** while the mon remains past the milestone.
- **No permanent opt-out**, no Everstone toggle, no manual evolve-now action.
- Eligibility ("past milestone, below `evo_seed` cap, not yet evolved") is **derived** from `level`/`evo_stage`/`evo_seed` — no new column.

### Source of truth

`xp` / `level` / `evo_stage` columns stay **authoritative for live reads** (battle/stat hot paths fold no ledger). The battle emits a **battle-result** history event for the timeline; this design does **not** require granular XP events. The event vocabulary and shapes are owned by [mon-event-history.md](mon-event-history.md).

### Tuning

All constants live in a new `progression` formulas module as **code constants** (matching `strength_formulas.py`, `strength.py`, encounter `tuning.py`) — semantically named and grouped (named growth-group dataclasses/enums, not bare floats), so every balance lever is legible in one place. Values marked `# TUNING TBD` for a dedicated balance pass:

- Growth groups + per-group `GROWTH_COEFF` and milestone levels.
- `evo_seed` birth weighting vs `intensity`.
- element → growth-rate and `evo_seed` → growth-rate bias tables (+ entropy spread).
- `BASE_YIELD`, `DIVISOR`, `PARTICIPATION_RATIO`, `evo_seed_weight`, `TRAINER_KILL_BOOST`.

## Implementation sketch

1. **Growth rate**: add the born growth-rate field + weighted birth roll (alongside the new weighted `evo_seed` roll, replacing `random_seed`).
2. **XP/level engine**: disposition-agnostic award + cubic curve in the `progression` module.
3. **Battle wiring**: post-battle resolves per-participant XP → level deltas → eligible evolutions; emits the battle-result event.
4. **Evolution**: recompute/persist `identity.base` at the new stage; owned-mon accept/cancel screen; wild auto-evolve.
5. **Moves**: on level-up, learn from the regenerated providers pool by `level_requirement`; offer/replace when full.

## Resolved (was Open Questions)

- **Tiers vs levels** → no separate tier; tier is derived from `level` + `evo_seed`.
- **Wild XP** → wild mons earn XP the same way (engine disposition-agnostic); the background wild-vs-wild *trigger* is deferred to [background-wild-simulation.md](background-wild-simulation.md).
- **Alumni** → reduced to a read-only roster of released mons; spun out to [alumni-roster.md](alumni-roster.md). Passive XP and mission-recruitment are cut.
- **Rare Candy / item leveling** → consistent with the model (an item granting XP/levels), but out of scope here.

## Anti-Goals

- No parallel tier ladder; no flat per-tier stat multipliers.
- No background wild-vs-wild simulation in this doc (engine is *ready* for it; the trigger is not built).
- No alumni passive XP or mission system.
- No full type-effectiveness matrix dependency.
