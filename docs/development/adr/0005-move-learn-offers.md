# Move learn offers sample four provider-eligible moves at battle end

**Status:** accepted

## Context

Vibemon birth materializes a per-mon learnset from the union of birth **Provider** move catalogs (plus universal moves in storage). At level-up, the progression engine must decide **when** to prompt learning, **which moves** are in play, and **how** the **Trainer** (or a **Wild** mon) resolves the choice.

Pokémon's natural cadence is: fill the four move slots early with low friction, then surface upgrade choices every ~6–8 levels once the kit is full. Vibemon's provider catalogs are large (~250+ moves per provider, ~65% at level 1) and birth only assigns 2–3 opening moves — so eligibility, sampling, and offer timing need explicit rules. Without them, the engine either floods the player with L1 junk or treats the full catalog union like a species learnset.

Domain terms: **Provider-Eligible Move**, **Move Learn Offer** (`docs/development/CONTEXT.md`).

## Decision

### Eligible pool

- A **Provider-Eligible Move** is a move from the mon's **birth Provider** catalogs where `level_requirement ≤ current level`.
- **Universal moves** enter the pool only as a **fallback** when fewer than four provider-eligible moves remain after exclusion. This path is expected to be rare.
- **Excluded from sampling:** any move ever **learned** (birth or kept) or **forgotten** (replaced off the active kit). Query history — not the active roster alone.
- **Not excluded:** rejected moves. A move declined in a prior offer can appear again at full weight.

### Offer shape

- Each **Move Learn Offer** presents **four distinct options**, sampled without replacement.
- Weight per candidate: `level_requirement ** exponent` (start with exponent **1.5**; tune in playtest). Higher-level moves skew toward novelty.
- The four options are **fixed when the offer is created**. Re-opening the UI must not re-roll.

### When offers fire

One offer maximum per mon per concluded battle.

| Phase | Trigger probability | Notes |
| :--- | :--- | :--- |
| **Fewer than four active moves** | **50%** per level jump | Flat per jump — not scaled by levels crossed in the jump |
| **Four active moves** | **`min(100%, levels_crossed × 15%)`** | Additive per level crossed; a +7 jump (or larger) guarantees an offer |

At ~15% per level with mostly +1 gains, owned mons see an offer roughly every **6–8 levels** on average. Variance (dry spells, back-to-back offers) is intentional.

### Trainer resolution (Owned)

- Offers are **ephemeral**: resolve on the battle screen before leaving. No pending offer survives navigation.
- UI is a **four-choice picker** in both phases. Below four slots, the chosen move fills an empty slot. At four slots, the player must replace an active move.
- **Declining is always allowed** — including while fewer than four moves are active. Declining the whole offer has no penalty; the next eligible level jump gets a fresh probability roll and a fresh sample.
- When multiple crew members qualify in one battle, offers resolve **sequentially**: active battler first, then bench by crew slot.

### Wild mons

- Same probability rules and weighting as owned mons.
- When an offer would fire, the engine auto-selects one weighted option. No UI.
- At four active slots, replace the active move with the **lowest `level_requirement`** (deterministic tie-break by slot order).

## Considered alternatives

- **Full birth-catalog union without provider scoping** — rejected. Treating ~500+ catalog moves as a level-up learnset cannot feel like Pokémon; early auto-learn would pull arbitrary L1 moves from unrelated providers.
- **Affinity `k=10` starter pool only** — rejected. Too thin (~15–25 moves); the four-picker would often show fewer than four options and exhaust the track by midgame.
- **Eligibility-gated offers** (fire only when the level jump crosses a `level_requirement` tier with new moves) — rejected in favor of flat probability. Gating tracks catalog density better but adds coupling to provider authoring; probability + exponential weighting achieves similar cadence with less branching.
- **Linear or stepped tier weighting** — rejected. `move_balance_reference.md` level bands govern **provider move authoring**, not gameplay sampling. Exponential weighting favors genuine novelty without mirroring catalog density tables.
- **Rejected moves deprioritized** — rejected. Second chances at full weight keep declined options viable without a separate "reminder" system.
- **Pending offers across sessions** — rejected. Pokémon resolves learn prompts in the victory beat; deferring to crew management adds stale-state complexity.
- **Wild mons: frozen kit at four moves** — rejected. Wild encounter supply would stagnate as mons level in the **Wild Pool**.

## Consequences

- `MoveLearnOffer` becomes a **bundle of four moves**, not a single move. Battle finish read models and progression persistence must carry the full sample.
- `learnable_moves()` (or its replacement) must project **learned ∪ forgotten** from `move_learned` / `move_forgotten` history events — not active slots only.
- Learn-offer sampling is **provider-catalog scoped** with a universal fallback branch; birth learnset storage may still include universal entries for catalog upsert, but they are not primary offer candidates.
- Wild progression needs an auto-resolve branch: weighted pick + lowest-`level_requirement` replacement heuristic.
- Battle finish UI needs a sequential offer flow when multiple mons qualify; each mon gets an independent roll and independent sample of four.
- Tuning knobs live in implementation (`15%`, `50%`, exponent `1.5`) — not in `CONTEXT.md`. Adjust via playtest if cadence feels too sparse or too busy.
