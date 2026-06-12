# Triage: Mons frequently receive type-antagonistic moves

**Date:** 2026-06-11
**Status:** Fixed — see "Implemented fixes" below
**Symptom:** Many mons carry moves whose type is disadvantaged against / opposite to their stated elements. Intended to be possible but rare; currently it is common.

## TL;DR

Move assignment happens in two stages, and **the second stage throws away type fit
entirely**. Each provider picks 10 type-biased starter moves against *its own local
typing*, then `Affinity.merge` resamples the final 2–3 moves from the pooled 40-ish
weighted only by provider intensity — uniform within a provider, blind to the mon's
*final* fused elements. A Monte Carlo against the real pipeline (climate=FIRE-leaning,
music=WATER-leaning, real `moves.json` catalogs) shows **~42% of mons end up with at
least one antagonistic move**, and ~20% of all assigned moves are antagonistic.

## How a move gets onto a mon (the trace)

1. **Provider catalogs** — each provider authors ~110–175 level-1 moves spread nearly
   uniformly across all 17–18 types (`app/providers/<name>/data/moves.json`), plus 2
   universal Normal moves (`app/domains/move/data/universal_moves.json`).

2. **Stage 1 — provider-local pick** (`app/providers/helpers.py:229`,
   `pick_starter_moves`). Each provider:
   - computes element `rankings` from its signals (`determine_element_scores`),
   - derives *provider-local* elements via `filter_element_types(rankings)`,
   - samples **k=10** moves without replacement, weighted by
     `clamp(rankings.get(move.type, 0.0) * get_move_assignment_bonus(...), 0.05, 2.0)`.
   The bonus (`app/domains/move/catalog.py:352`) is 2.0 same-type / 1.5 coverage /
   1.0 normal / 0.5 antagonistic.

3. **Stage 2 — birth merge** (`app/domains/generation/affinity.py:74`,
   `Affinity.merge`, called from `birth_outcome_from_affinities`):
   - final elements come from `fuse_element_rankings` + `filter_element_types`
     (peak-normalized across providers),
   - final moves come from `weighted_sample(pool, k=rng.randint(2,3))` at
     `affinity.py:117`, where the pool is every provider's 10 picks and **each move's
     weight is just `int(provider_intensity * 100)`** (`affinity.py:105`).

## Root causes, in order of impact

### 1. Stage 2 ignores type fit (primary)

`affinity.py:105` gives every move from the same provider an identical weight. Within
a provider's 10 picks, an antagonistic filler move has *exactly the same* final-sample
probability as a perfect same-type move. `get_move_assignment_bonus` is never consulted
against the **fused** elements — its only call site is stage 1
(`helpers.py:263`), against provider-local elements.

This also creates a cross-provider mismatch: when providers disagree (climate says
FIRE, music says WATER), the fused typing may land on one side, but the other
provider's 10 moves — biased toward the *losing* typing — sit in the pool at full
intensity weight.

### 2. The 0.05 weight floor carries ~19% of stage-1 mass

In `pick_starter_moves`, every move whose type has no ranking score gets
`clamp(0.0 * bonus, 0.05, 2.0) = 0.05`. With ~130 unranked moves in a ~160-move
catalog, the floor alone is `130 × 0.05 ≈ 6.5` of total mass ≈ **19%**. Measured:
even sampled against the provider's *own* elements, **~16–18% of stage-1 picks are
antagonistic** regardless of k. The floor is absolute, but the mass it controls scales
with catalog size — it was presumably tuned for a much smaller pool.

Representative weight histogram (climate catalog, FIRE=1.0 / GROUND=0.5 / ROCK=0.3):

| weight | moves | share of mass |
|-------:|------:|--------------:|
| 2.00 (same-type) | 9 | 54.0% |
| 0.75 (coverage)  | 10 | 22.5% |
| 0.15 (antagonistic, ranked) | 10 | 4.5% |
| 0.05 (floor, unranked) | 127 | **19.0%** |

### 3. The 2.0 weight ceiling erases the bonus at provider score scales (secondary)

Stage-1 rankings are **not normalized** and providers use different scales — biome
sums lookup weights, climate adds unclamped WeatherCode bonuses (this is exactly why
`fuse_element_rankings` peak-normalizes at merge time; stage 1 never does). When a
type's score is ≥ 4.0, same-type (`s × 2.0`) and antagonistic (`s × 0.5`) both clamp
to 2.0 and the bonus does nothing. Measured: same-type share of stage-1 picks drops
from 47% (peak score 1.0) to 33% (peak 5.0).

### 4. k=10 without replacement depletes the good candidates (minor)

With only ~9–10 same-type moves in a catalog, drawing 10 without replacement forces
tail moves into the back half of the picks. Measured effect is small (same-type share
52% at k=3 → 48% at k=10) — but it means each provider's hand of 10 *always* contains
floor moves for stage 2 to pick blindly.

## Why it surprises Trainers

The design intent (per the `get_move_assignment_bonus` docstring) is a 4:1
same-type:antagonistic odds ratio. The realized end-to-end odds are roughly 2:1
per move, and with 2–3 moves per mon the chance of at least one antagonistic move
compounds to ~40%+ whenever providers disagree on typing.

## Implemented fixes

1. **`Affinity.merge` re-weights the final sample against the fused elements**
   (`affinity.py`): each pooled move's weight is now
   `provider_intensity × get_move_assignment_bonus(move.type, fused_elements)`,
   so the final gate respects the mon's actual typing no matter what stage 1
   produced.
2. **Elemental opposition trumps coverage** (`catalog.py`,
   `get_move_assignment_bonus`): if any of the mon's own elements resist — or are
   immune to — the move's type (`ELEMENT_CHART[(move_type, element)] < 1.0`), the
   bonus is capped at the antagonistic 0.5×, even when the move would otherwise earn
   the coverage bonus. Rationale: a water creature shouldn't breathe fire; FIRE
   technically covers WATER's grass weakness, but the thematic opposition should
   dominate. Same-type still wins first (FIRE resists FIRE, but a FIRE move on a
   FIRE mon is the definition of thematic fit).
3. **`pick_starter_moves` peak-normalizes rankings and uses a relative floor**
   (`helpers.py`): rankings are scaled to peak 1.0 (mirroring
   `fuse_element_rankings`) so the same-type bonus is never flattened for sum-scale
   providers, and the old `clamp(…, 0.05, 2.0)` is replaced by a 0.01 floor —
   unranked move types stay possible without their combined mass growing with
   catalog size.

Not done (judged unnecessary after the above): reducing stage-1 k from 10.

Note: these change sampling under existing `BirthSnapshot` replay — per the
rebalance philosophy this is acceptable (re-score frozen payloads, don't preserve
historical rolls), but rebalanced mons will get different moves.

## Post-fix measurements

Same Monte Carlo harness as below, after the fixes:

```
Scenario A (providers disagree, fused FIRE/WATER):
  per-move fit: same-type 70.1% | coverage 19.9% | normal 0.3% | antagonistic 9.7%
  mons with >=1 antagonistic move: 22.3%   (was 41.8%)
  moves the mon's own typing resists:  7.9%
Scenario B (providers agree, mono-WATER):
  per-move fit: same-type 91.2% | coverage 2.9% | antagonistic 5.5%
  moves the mon's own typing resists:  2.4%
P(mono-WATER mon carries a FIRE move): 0.65%  (N=20,000)
```

Opposed moves remain *possible* (no weight is ever zero) but are now genuinely
rare. Scenario A's residual 22% includes the resist cap reclassifying many
would-be "coverage" types as antagonistic — a dual FIRE/WATER mon resists 9
move types, so the 4:1 design odds simply have more antagonistic candidates to
apply to. Verified: full backend suite passes (345 passed; the pre-existing
`test_celestial_balance_smoke.py` collection error — missing
`scripts.rehearse_celestial_balance` module — is unrelated).

## Reproduction

Monte Carlo (N=3000) with real `pick_starter_moves` + `Affinity.merge` sampling logic
and real catalogs; climate rankings {FIRE 2.2, GROUND 1.1, ROCK 0.6} @ intensity 0.8,
music {WATER 3.0, ICE 2.1, FAIRY 1.0} @ 0.6 → fused typing (FIRE, WATER):

```
per-move fit: same-type 37.4% | coverage 41.5% | normal 1.1% | antagonistic 20.0%
mons with ≥1 antagonistic move: 41.8%
```
