# Achievement System

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | Medium–High |
| **Area** | Meta-Progression & Discovery |
| **Related** | [vibemon-xp-and-evolution.md](vibemon-xp-and-evolution.md), [vibe-gold-economy.md](vibe-gold-economy.md), [mon-event-history.md](mon-event-history.md), [generative-aesthetics-and-showcase.md](generative-aesthetics-and-showcase.md), [geolocation-traversal-and-simulation.md](geolocation-traversal-and-simulation.md), [posthog-analytics-day-one.md](posthog-analytics-day-one.md) |

## Summary

Lightweight milestones that celebrate the full **Vibemon** loop — birth, review, adoption, exploration, battle, and showcase — without turning progression into a grind checklist. Achievements nudge discovery (providers, biomes, tactics) and give the Alumni Roster and Trainer Card something worth showing off.

## Problem

Trainers need recognition for verbs, not vanity stats. Without time-calibrated gates, achievements either feel trivial or impossible. Deferred features (catch, weather, simulated travel) must not block v1 families while leaving room to extend when telemetry ships.

## Concept

A **five-tier performance ladder** (Day One → Encore) with **multi-level achievement families** (one thematic track, five gates per family) plus standalone discovery moments. Gates assume ~30 min/day battle time and ~30 min/week generation; tune from PostHog after launch.

## Design

### Tier ladder (5 tiers)

Five pithy labels that read as one performance arc — **show up → find the groove → nail it → top billing → they beg you back**. Tier labels describe *skill stage*; **duration targets** describe when an average trainer should clear that tier's gates.

| Tier | Label | Performance stage | Duration target |
|------|-------|-------------------|-----------------|
| 1 | **Day One** | Learning the loop | **1 week** |
| 2 | **On the Beat** | Forming habits | **2 weeks** |
| 3 | **In the Pocket** | Competent regular | **1 month** |
| 4 | **Headliner** | Sustained skill | **3 months** |
| 5 | **Encore** | Long-term mastery | **6 months** |

**Naming rationale**
- Tiers 1–3 are warm-up through mastery — performance metaphor, not calendar labels.
- **Headliner** = top billing; **Encore** = the crowd calls you back.
- Share copy: *"Encore — Wild Pool Sovereign."*

---

### Play model (gate calibration)

Gates assume a **typical** trainer — not a speedrunner, not a weekend-only player.

| Assumption | Value |
|------------|-------|
| Battle time | **30 min / day** |
| Generation time | **30 min / week** (candidates: birth + review) |
| Battle length | **8 turns** × **~2 min / turn** ≈ **16 min / battle** |
| Battles / day | 30 ÷ 16 ≈ **1.9** (~**13 / week**) |
| Candidates / week | 30 min gen ÷ ~8 min / cycle ≈ **4** |
| Win rate | **70%** of battles |
| Flawless win rate | **~20%** of wins (skill-gated; grows slowly) |
| Adoption rate | **~60%** of reviewed candidates |
| Christen / manifest | **~90%** of adoptions (lifecycle lag absorbed in month+ gates) |

### Projected cumulative activity

Rounded from the model above; gates sit at **~85–90%** of these values so on-schedule play clears each tier on time with slight slack.

| Horizon | Battles | Wins | Candidates | Reviews | Adoptions | Flawless wins | Distinct moves | Ever-owned |
|---------|---------|------|------------|---------|-----------|---------------|----------------|------------|
| **1 week** | 13 | 9 | 4 | 4 | 2 | 2 | 5 | 3 |
| **2 weeks** | 26 | 18 | 8 | 8 | 5 | 4 | 9 | 6 |
| **1 month** | 53 | 37 | 16 | 16 | 10 | 7 | 16 | 12 |
| **3 months** | 159 | 111 | 48 | 48 | 29 | 22 | 30 | 35 |
| **6 months** | 318 | 223 | 96 | 96 | 58 | 45 | 48 | 70 |

**Scaling philosophy**
- **Count families** (wins, reviews, births, alumni): gates track projected activity at each horizon.
- **Skill families** (Clean Sweep): gates stay well below win totals — perfection scales with ability, not hours.
- **Catalog families** (Type Tourist, Move Catalog Scholar): gates asymptote toward finite roster / move catalog size; Encore = complete the set.
- **Encore** targets **~6 months** of typical play per family — aspirational but reachable, not multi-year.

Tune gates ±15% after launch if PostHog shows tier completion clusters drifting from targets.

---

### Multi-level achievements

Most achievements are **families** — one thematic track with **five gates**, one per tier.

**Example — Review Regular**

| Tier | Display title | Gate | Target horizon | Flavor |
|------|---------------|------|----------------|--------|
| Day One | **Curious Glance** | 3 reviews | 1 week | You looked. That counts. |
| On the Beat | **Review Regular** | 7 reviews | 2 weeks | Curator of your own supply chain. |
| In the Pocket | **Candidate Connoisseur** | 15 reviews | 1 month | Picky, but in a good way. |
| Headliner | **Wild Pool Editor-in-Chief** | 45 reviews | 3 months | The **Wild Pool** reads your mood board. |
| Encore | **Wild Pool Sovereign** | 90 reviews | 6 months | You don't browse. You mandate. |

**UX notes**
- Family card shows **five pips**; **Encore** pip is visually distinct (e.g. prismatic ring).
- Progress bar targets the **next** gate only.
- **Headliner** gates: hide exact number until ≥80%.
- **Encore** gates: hidden until the Headliner gate in that family is unlocked; then show `???` until ≥50% progress.
- Encore has **no Vibe Gold drip** per gate — prestige is cosmetic (titles, frames, animated Trainer Card flourish).

**v1 totals:** 10 families × 5 gates = **50** + **10** standalone = **60** achievements.

---

### Design principles

1. **Celebrate verbs, not stats.** Prefer "Win a battle at dusk" over "Deal 10,000 damage."
2. **Respect deferred features.** Catch-from-battle and weather achievements stay in *Future* until shipped.
3. **No pay-to-win hooks.** Achievements unlock cosmetics, titles, and Trainer Card flair — not battle power.
4. **Provider-aware.** Music, climate, and biome paths each get discovery moments.
5. **Alumni-safe.** Milestones that count released Vibemon read as "journey," not punishment for **Release**.
6. **Time-calibrated.** Each tier's gates should clear within its duration target for a 30 min/day trainer; adjust when real telemetry diverges.

---

### Achievement families (50)

Each row is one family; columns are tier gates calibrated to **1 wk / 2 wk / 1 mo / 3 mo / 6 mo**.

### Generation & lifecycle

| Family | Day One (1 wk) | On the Beat (2 wk) | In the Pocket (1 mo) | Headliner (3 mo) | Encore (6 mo) |
|--------|----------------|--------------------|-----------------------|------------------|---------------|
| **Birth Certificate** *(candidates generated)* | 3 | 7 | 15 | 45 | 95 |
| **Signed & Sealed** *(adoptions)* | 2 | 5 | 10 | 28 | 55 |
| **Name Tag Energy** *(christens)* | 2 | 4 | 9 | 25 | 50 |
| **Fully Realized** *(manifests)* | 2 | 4 | 9 | 25 | 50 |

**Birth Certificate** tier titles: **First Soundtrack** → **On Repeat** → **Local Legend** → **Birth Context VIP** → **Generational Artist**

### Battle & review

| Family | Day One (1 wk) | On the Beat (2 wk) | In the Pocket (1 mo) | Headliner (3 mo) | Encore (6 mo) |
|--------|----------------|--------------------|-----------------------|------------------|---------------|
| **Contact Continuum** *(wins in **Actual Encounters**)* | 7 | 15 | 35 | 105 | 210 |

*v1 **Contact Continuum** counts **wins only**. Most trainer battle time is vs **Wild** **Vibemon** (win or **Defeat** / flee) — see [Future: Wild encounters](#future-wild-encounters).*
| **Review Regular** *(candidate accept/reject)* | 3 | 7 | 15 | 45 | 90 |
| **Clean Sweep** *(wins with no crew faints)* | 2 | 3 | 7 | 20 | 42 |
| **Move Catalog Scholar** *(distinct moves used in battle, lifetime)* | 4 | 8 | 14 | 28 | 48* |

\*Encore gate = **min(48, 90% of published catalog)**. Revisit when **Move Catalog** grows.

**Contact Continuum** tier titles: **First Contact** → **Regular Fixture** → **Wild Pool Nemesis** → **Encounter Endgame** → **The Pool Knows You**

**Clean Sweep** tier titles: **Flawless Debut** → **Clean Routine** → **Sweep Specialist** → **Untouchable Roster** → **Ghost Touch**

### Collection & roster

| Family | Day One (1 wk) | On the Beat (2 wk) | In the Pocket (1 mo) | Headliner (3 mo) | Encore (6 mo) |
|--------|----------------|--------------------|-----------------------|------------------|---------------|
| **Type Tourist** *(distinct elements ever owned)* | 2 | 3 | 5 | 9 | 12† |
| **Alumni Wall of Fame** *(unique **Vibemon** ever **Owned**, including those returned to **Wild** via **Release**)* | 3 | 6 | 11 | 32 | 65 |

†Encore gate = **every element in the live roster** (currently 12). Gate tracks `count(all_elements)` if roster expands.

**Type Tourist** tier titles: **Dual Type Curious** → **Type Tourist** → **Element Polyglot** → **Periodic Table Flex** → **Omnitype Orbit**

**Alumni Wall of Fame** tier titles: **Roster Starter** → **Regular Collector** → **Alumni Archivist** → **Hall of Fame** → **Living Archive**

---

### Standalone achievements (10)

Discovery moments that don't ladder on counts. Placed so they land within the same duration window as their tier.

| Tier | Target | Title | Trigger | Flavor |
|------|--------|-------|---------|--------|
| Day One | 1 wk | **Hello, World** | Complete trainer registration | Every legend starts somewhere. Usually a username field. |
| Day One | 1 wk | **Timeout Artist** | Let a **Candidate Review** expire into **Wild** | Hesitation is also a choice. The **Wild Pool** agrees. |
| Day One | 1 wk | **Sound Check** | First birth with **Music Provider** opted in | Your playlist finally fights back. |
| On the Beat | 2 wk | **Climate Control** | First birth with **Climate Provider** contributing | The sky had opinions. You listened. |
| On the Beat | 2 wk | **Grounded** | First birth with **Biome Provider** contributing | Local soil, local soul. |
| On the Beat | 2 wk | **Full Stack** | One birth with climate + biome + music all opted in | Maximum context. Maximum chaos. |
| In the Pocket | 1 mo | **Release Valve** | **Release** your first **Owned** **Vibemon** to **Wild** | Every **Alumni Roster** starts with goodbye. |
| In the Pocket | 1 mo | **Coastline Cartographer** | Win an **Actual Encounter** in a coastal **Wild Geography Bucket** | Salt in the air, types in the grass. |
| In the Pocket | 1 mo | **Night Owl** | Win a battle during **Solar Phase** `night` | The **Birth Context** moon approves. |
| Headliner | 3 mo | **High Roller** | Win a **Vibe Gold** wager with ≥500 VG staked | Escrow closed. Vibes paid out. |

**Standalone dependency flags**
- **Coastline Cartographer** — requires a *coastal* classification in the **Wild Geography Bucket** taxonomy. Confirm the taxonomy carries terrain class before committing; otherwise demote to Future with **Geography Passport**.
- **Night Owl** — requires **Solar Phase** computed at *battle* time. Today solar phase derives from **Birth Context**; battle context must capture it too (same listed blocker as **Solar Serenade**).
- **High Roller** — blocked by the **Vibe Gold** wager economy ([vibe-gold-economy.md](vibe-gold-economy.md)). If economy slips, Headliner ships with 0 standalones (acceptable — see Tier balance).

*Future Encore standalone (expansion): **Whale Song** — win a wager with ≥5,000 VG staked.*

---

### Tier balance

| Tier | Duration | Family gates | Standalone | Total |
|------|----------|--------------|------------|-------|
| Day One | 1 week | 10 | 3 | 13 |
| On the Beat | 2 weeks | 10 | 3 | 13 |
| In the Pocket | 1 month | 10 | 3 | 13 |
| Headliner | 3 months | 10 | 1 | 11 |
| Encore | 6 months | 10 | 0 | 10 |
| **Total** | | **50** | **10** | **60** |

---

### Gate vs. model check

How rescaled gates compare to projected activity at each horizon (~90% target band).

| Family | 1 wk gate → proj | 2 wk → proj | 1 mo → proj | 3 mo → proj | 6 mo → proj |
|--------|------------------|-------------|-------------|-------------|-------------|
| Contact Continuum | 7 → 9 | 15 → 18 | 35 → 37 | 105 → 111 | 210 → 223 |
| Review Regular | 3 → 4 | 7 → 8 | 15 → 16 | 45 → 48 | 90 → 96 |
| Birth Certificate | 3 → 4 | 7 → 8 | 15 → 16 | 45 → 48 | 95 → 96 |
| Clean Sweep | 2 → 2 | 3 → 4 | 7 → 7 | 20 → 22 | 42 → 45 |
| Alumni Wall of Fame | 3 → 3 | 6 → 6 | 11 → 12 | 32 → 35 | 65 → 70 |

---

### Future: wild encounters

v1 achievement gates are calibrated around **generation** (credits, review, adoption) and **wild wins**. That underweights how trainers actually spend battle time: most fights are **Actual Encounters** vs **Wild** **Vibemon**, and many end in **Defeat** or flee — not just wins.

**Design intent when wild battle telemetry ships**
- Track **wild battles completed** separately from **wild wins** (outcome-agnostic).
- **PvP / wager battles** stay on their own counters — do not inflate wild engagement metrics.
- PostHog: extend `battle_ended` with `opponent_disposition: wild | pvp`, `outcome: win | defeat | flee`.

**Play model adjustment (wild battles, any outcome)**

At 30 min/day and ~16 min/battle → ~**13 wild battles / week** (vs ~**9 wins** at 70% win rate):

| Horizon | Wild battles | Distinct wild elements faced* |
|---------|--------------|--------------------------------|
| 1 week | 13 | 2–3 |
| 2 weeks | 26 | 4 |
| 1 month | 53 | 5–6 |
| 3 months | 159 | 9 |
| 6 months | 318 | 12 (all) |

\*Assumes local biome diversity early; **Simulation Vacation** and travel widen type exposure in later tiers.

**Why this matters for achievements**
- **Contact Continuum** (v1): wins only — rewards skill.
- **Wild Scuffle** (future): any completed wild battle — rewards showing up.
- **Type Crossed** (future): distinct **Elements** on the **opposing** wild **Vibemon** — rewards exploration and matchup breadth; complements **Type Tourist** (elements ever **Owned**).

---

### Future families (when features land)

Calibrated to the same play model and duration targets.

| Family | Gates (1 wk / 2 wk / 1 mo / 3 mo / 6 mo) | Blocked by |
|--------|--------------------------------------------|------------|
| **Wild Scuffle** *(wild battles completed; win, **Defeat**, or flee)* | 10 / 22 / 45 / 135 / 270 | Outcome-agnostic wild battle counter |
| **Type Crossed** *(distinct wild opponent **Elements** faced; win or lose)* | 2 / 4 / 6 / 9 / 12‡ | Wild opponent element on `battle_ended` |
| **Gotcha** *(catch adoptions)* | 2 / 5 / 10 / 28 / 55 | **Catch** flow (deferred) |
| **Provider Trinity** *(all-3-provider births)* | 1 / 2 / 4 / 12 / 25 | v1 uses **Full Stack** standalone |
| **Crew Line** *(crew slots filled; max 6)* | 1 / 3 / 4 / 6 / 6 all **Manifest** | Crew UX polish |
| **Simulation Vacation** *(simulated travel sessions)* | 1 / 1 / 2 / 4 / 8 | Simulated travel perk |
| **Geography Passport** *(distinct geography buckets)* | 2 / 3 / 5 / 8 / all | Bucket taxonomy |
| **Solar Serenade** *(wins per solar phase)* | 1 / 3 / 8 / 22 / 45 per phase | Solar phase on battle context |
| **Evolution Escalator** *(vibemon evolution tiers)* | 1 Adept / 2 Adept / 1 Expert / 1 Master / 3 Masters | XP & evolution system |
| **Weather Worker** *(weather set + win)* | 2 / 5 / 12 / 35 / 70 | Field weather on **Battle** |

‡**Type Crossed** tier 1 (Day One, **1 week**): battle wild **Vibemon** of **2** distinct **Elements** — win or lose. This is the first step toward **Battled All Types**; Encore = every element in the live roster faced at least once in a wild **Actual Encounter**. Tier titles: **Type Tapped** → **Type Tested** → **Type Traveled** → **Type Tempered** → **Omnitype Opponent**.

*Optional Day One standalone when **Type Crossed** ships (same trigger as tier 1 gate): **Type Tapped** — "First wild matchup logged. Win optional."*

---

### Rewards (non-power)

| Reward type | Tier scope | Examples |
|-------------|------------|----------|
| **Trainer titles** | All tiers | Equip highest unlocked family title |
| **Showcase frames** | In the Pocket+ | Tier-colored **Alumni Roster** borders |
| **Emote unlocks** | On the Beat+ | Crew screen reactions |
| **Vibe Gold drip** | Day One–Headliner only | Small one-time VG bonus per **tier completion** (all gates in that tier) |
| **Family flourish** | Headliner (4/5 gates) | Animated badge on Trainer Card |
| **Encore flourish** | Encore (5/5 gates) | Prismatic Trainer Card treatment + unique emote; **no VG** |

Completing **every Encore gate across all families** (10/10 at tier 5) unlocks a **seasonal prestige border**.

*Reward dependency:* **Vibe Gold drip** requires the economy to ship; **Showcase frames** require the Alumni Roster surface ([generative-aesthetics-and-showcase.md](generative-aesthetics-and-showcase.md)). v1 can ship with **titles only** as the reward layer — titles need nothing but a Trainer Card surface.

---

## Surface & routing

The **Vibe Deck** is the app shell hub (`/deck`, currently redirecting to `/deck/crew`). Diegetically the deck is the trainer's field device — crew index, encounter reference, capture interface — and it already stores trainer identity, so the **Trainer Card** belongs *inside* it.

**Recommendation: `/deck/trainer` — a Trainer Card screen, with achievements as its main body.**

- Achievements are trainer meta-progression, not a **Vibemon**-collection view, so they don't belong under `/deck/crew`.
- A dedicated top-level `/achievements` route fragments navigation for a feature whose rewards (titles, frames, flourishes) all render *on* the Trainer Card anyway.
- v1 Trainer Card scope is deliberately thin: username, equipped title, achievement family grid (five pips per family), standalone list. Avatar/reference art, share-export, and frames arrive with the showcase idea.
- The family detail view (progress bar to next gate, flavor text) can be a drawer/modal within `/deck/trainer` — no extra route.

This also gives **Hello, World** (registration), titles, and the future share-export Trainer Card one canonical home.

---

## Risks

1. **No authoritative event source exists yet.** PostHog is analytics, not game state — ad-blocked clients would lose unlocks, and the doc already requires backend-authoritative grants. But the backend currently persists no battle results, no per-turn move usage, and no per-trainer counters. Biggest hidden cost of this idea: a **trainer activity ledger** (or per-family counters incremented inside the adoption/battle/birth workflows). Decide ledger-vs-counters before any UI work.
2. **"Distinct moves used in battle, lifetime" needs per-turn logging.** Move Catalog Scholar requires recording which **Move** each **Battle Action** used, per trainer, forever. That's a new write path in battle resolution, not a counter bump.
3. **Backfill / retroactivity.** Trainers who played before launch: derive what we can from existing tables (adoptions, christens, manifests are persisted) and accept zero-start for battle counters — state this in player copy, or early adopters feel robbed.
4. **Append-only grants vs. dynamic gates.** Type Tourist and Move Catalog Scholar Encore resolve against live catalog size. If the catalog grows after a grant, the unlock stays (append-only) but the family reads "complete" while no longer being so. Pick a rule: grants are forever, gate text shows the catalog size *at grant time*.
5. **Timeout Artist incentive.** Rewarding a **Candidate Review Timeout** burns a **Generation Credit** for an achievement. One-time and Day One-tier, so cheap — but confirm credit economics tolerate a deliberate waste before keeping it.
6. **Calibration model is fully synthetic.** Every gate derives from assumed 30 min/day play with zero telemetry behind it. The ±15% tuning plan is right, but expect *tier-wide* rescales, not nudges — keep gates in data/config, never hardcoded, so a rebalance is a data change.
7. **Cross-idea coupling.** Alumni Roster, Trainer Card export, Vibe Gold, and wagers are all *other* idea docs. v1 achievements should depend only on: trainer profile screen (this doc), existing adoption/birth state, and new battle counters.

---

## Implementation

- **Event source:** Backend is authoritative. Unlock checks run inside the owning workflow (adoption, battle resolution, birth) against backend counters; PostHog mirrors for analytics only and never grants.
- **Counters:** Per-trainer activity counters (or an activity ledger — see Risks #1) incremented in workflows. Gates live in data/config, not code, so calibration rescales are data changes.
- **Schema:** `achievement_family_id`, `tier` (1–5), `threshold`, `unlocked_at`. One row per `(trainer_id, family_id, tier)`.
- **Dynamic gates:** Type Tourist Encore and Move Catalog Scholar Encore resolve against live catalog size at check time.
- **Idempotency:** Grants are append-only.
- **Privacy:** Location achievements use coarse **Wild Geography Bucket**, never raw coordinates.
- **Progress UI:** Five pips; Encore pip locked until Headliner gate cleared; Encore progress obfuscated until 50%.
- **Calibration:** Track `median_days_to_tier_unlock` per family; target bands are 7 / 14 / 30 / 90 / 180 days.

## Success Criteria

- Tier completion clusters within ±15% of duration targets after launch telemetry.
- v1 ships 60 achievements (50 family gates + 10 standalone) without catch/weather dependencies.
- Encore gates feel aspirational at ~6 months typical play, not multi-year.

## Open Questions

- When wild battle telemetry ships, split **Contact Continuum** (wins) from **Wild Scuffle** (any outcome)?
- Encore VG drip: intentionally zero — revisit if economy needs more sinks?
- Counter storage: dedicated per-family counters vs. a generic trainer activity ledger replayed into counters? Ledger is more flexible for future families but a bigger lift.
- Does the **Wild Geography Bucket** taxonomy carry a terrain class (coastal) today, or does **Coastline Cartographer** move to Future?
