# Vibemon Move Balance Reference

Ground truth for move generation in Vibemon. Read **§1 Design Philosophy** and **§2 Decision Flow** before any table — the tables are constraints; those two sections are the *logic* you apply.

Vibemon caps learnsets at **`MAX_LEVEL = 100`** (`backend/app/const.py`).

The battle engine uses the modern mainline Pokemon-style integer damage formula:
base damage floors at intermediate steps, critical hits use a 1.5x modifier, random damage is an integer roll
from 85 through 100, STAB is 1.5x, type immunity deals exactly 0 damage, and damage is clamped to at least 1 only
after confirming the hit was not immune. At level 1, generated Vibemon usually have about 12-15 HP and attacking
stats near 5-8, so 75-100 power moves are not "starter" moves; they are 2HKO/OHKO pressure.

---

## 1. Design Philosophy

Every Vibemon move is a **tradeoff across four dials**:

| Dial | What it controls | Direction of pressure |
|---|---|---|
| **Power** | Damage per hit | ↑ pulls every other dial down |
| **Accuracy** | Hit reliability | Drops as power rises |
| **PP** | Uses per battle | Drops as power rises |
| **Level requirement** | When the Vibemon learns it | Rises with power *and* with team-warping utility |

**The rule:** a move that is strong on one dial must be weak on another. The whole reference below is just bookkeeping for that rule.

- **Flamethrower** (90 / 100% / 15 PP) — "balanced workhorse." Strong on every dial, exceptional on none.
- **Fire Blast** (110 / 85% / 5 PP) — pays for +20 power with –15% accuracy and –10 PP.
- **Hyper Beam** (150 / 90% / 5 PP, must recharge) — pays for raw power with a *whole turn* of vulnerability.
- **Tackle** (40 / 100% / 35 PP) — "you can spam it" is itself the design; the low power is the cost of that spammability.

Two secondary axes ride on top of those four dials:

- **Type → Category fit.** Each type has a natural physical/special leaning rooted in flavor (FIRE = special because flames radiate; FIGHTING = physical because fists). Crossing the natural category is allowed when the *flavor* of the specific move justifies it (Flare Blitz = a body slam *that happens to be on fire* → physical).
- **Secondary-effect budget.** Two layers here: *whether* a damaging move carries a rider at all, and *how often* it procs. In canon Vibemon only **~25–30% of damaging moves carry a secondary effect** — the default for a damaging move is **no rider**. When a rider is present, its chance scales **inversely** with power: a 40 BP move can paralyze 30% of the time; a 110 BP move gets 10% at most, or pays via accuracy/PP instead.

---

## 2. Decision Flow (apply in order)

When generating any move, walk these steps top to bottom. Earlier steps constrain later ones.

1. **Theme / Type** — what is this move *about*? (volcanic eruption, mind trick, vine whip)
2. **Category** — Physical / Special / Status. Default to the type's natural category (§4); cross only if flavor demands it.
3. **Power tier** — pick a band from §3 based on how impactful the move should feel. This single choice locks most of the next two steps.
4. **PP & Accuracy** — read straight off §3 from the power tier. Adjust within the band only with a *reason* (e.g. "this is the signature finisher, drop accuracy to 85%").
5. **Level requirement** — combine power tier (§7) with role in the learnset (§5–§6). About **70%** of any batch should still be at level 1, but level-1 damaging moves must stay in starter power bands.
6. **Secondary effect** — *first decide whether the move has one at all.* For damaging moves, default to **no rider** (~70% of damaging moves should have none); add one only if the theme calls for it. If you do add one, pick a status / stat change consistent with the theme (§10) and set its chance per §8: the stronger the move, the rarer the proc. Status-category moves always have an effect (the effect *is* the move).
7. **Sanity check** — run the §11 anti-pattern list. If the move violates any, weaken a dial.

---

## 3. Power × PP × Accuracy: The Core Tradeoff

The spine of the whole system. *If you set power, the other two are 80% determined.*

| Power | Typical PP | Typical Accuracy | What this tier *is* | Real anchors |
|---|---|---|---|---|
| **None (Status)** | 10–20 | 1.0 (or 0.75–0.9 if the effect is huge) | Utility — PP set by §6, not by damage | Swords Dance (—/100%/20), Thunder Wave (—/90%/20), Sleep Powder (—/75%/15), Stealth Rock (—/100%/20) |
| **10–30** | 25–40 | 1.0 | Chip damage / spammable | Pound, weak jabs, soft openers |
| **35–55** | 20–30 | 1.0 | Early-game STAB; reliable filler | Tackle (40/100%/35), Ember (40/100%/25), Water Gun (40/100%/25), Vine Whip (45/100%/25) |
| **65–80** | 15–20 | 0.95–1.0 | Mid-game upgrade tier | Bubble Beam (65/100%/20), Flame Wheel (60/100%/25), Aerial Ace (60/—%/20, never miss) |
| **80–100** | 10–15 | 0.9–1.0 | The "always good" workhorses; competitive kit | Flamethrower (90/100%/15), Surf (90/100%/15), Ice Beam (90/100%/10), Earthquake (100/100%/10), Thunderbolt (90/100%/15) |
| **100–110** | 5–10 | 0.8–1.0 | Reliable high power; one dial usually pays | Hydro Pump (110/80%/5) — pays in accuracy *and* PP |
| **110–120** | 5–10 | 0.7–0.9 | Power-vs-accuracy bites hard | Thunder (110/70%/10), Fire Blast (110/85%/5), Focus Blast (120/70%/5) |
| **120–150** | 5 | 0.7–0.9 | Signature / finishers — must hurt to use | Megahorn (120/85%/10), Stone Edge (100/80%/5, high crit) |
| **150+** | 5 | 0.9 | Always has a *major* drawback baked in | Hyper Beam (150/90%/5, recharge), Explosion (250/100%/5, user faints), Self-Destruct (200/100%/5, user faints) |

**Logic checks before finalizing any damaging move:**
- Power ≥ 100, accuracy = 100%, PP ≥ 15 → **too strong on every dial. Cut one.**
- Power ≤ 60, accuracy < 1.0 → **why does a cheap move miss? Bump to 100% unless flavor demands.**
- Power ≥ 120 with no drawback (acc penalty, recharge, recoil, 5 PP, or self-debuff) → **add one.**
- 5 PP on a sub-100-power move → **suspicious; only Status moves and signature 100+ tier earn 5 PP.**

---

## 3.5. Power-Band Distribution Quotas (per batch)

§3 anchors *each* move; §3.5 anchors *the batch*. Without quotas, batches drift toward the comfortable middle (65–100 BP) and capstones / spam tiers vanish. The targets below apply to **damaging moves only** (status moves are sized separately by §6 / §7).

Let `D` = damaging move count in the batch.

| Tier label  | Power     | Share of `D` | Per-tier floor | Real anchor                      |
|-------------|-----------|--------------|----------------|----------------------------------|
| `spam`      | 10–30     | 5–10%        | `≥0.5×target`  | Tackle, Pound, Vine Whip (45)    |
| `early-stab`| 35–55     | 15–20%       | `≥0.5×target`  | Tackle, Ember, Water Gun         |
| `mid`       | 65–80     | 25–30%       | `≥0.5×target`  | Bubble Beam, Flame Wheel         |
| `workhorse` | 80–100    | 25–30%       | `≥0.5×target`  | Flamethrower, Surf, Earthquake   |
| `high`      | 100–120   | 10–15%       | `≥0.5×target`  | Hydro Pump, Thunder, Fire Blast  |
| `signature` | 120+      | 3–7%         | `≥1` (capstone)| Megahorn, Focus Blast, Hyper Beam|

**Hard rules:**
- **Floor**: each tier's realized count must be `≥ 50%` of its target.
- **Ceiling**: no single tier may hold `> 40%` of `D`.
- **Capstone**: every batch ships at least one signature (`power ≥ 120`) somewhere.

### Spam-tier worked example — "Tackle"

| Dial            | Value   | Reasoning |
|-----------------|---------|-----------|
| Type            | NORMAL  | Theme: bare-bones body check |
| Category        | Physical| Natural lean |
| Power           | 40      | Spam tier (§3 row 10–30 / 40–60 boundary) |
| Accuracy        | 100%    | Cheap moves should hit |
| PP              | 35      | Top of high-PP band — the *spammability* is the design |
| Level requirement | L1    | §7 weak-damage band, §6 L1 pool |
| Secondary       | none    | Cheap moves rarely carry riders (§8a) |

Sanity: power is the cost of high PP, not vice versa. ✅

---

## 3.6. Priority Dial

`schema.Move.priority` is the **turn-order dial** (range `−7..+7`, default `0`). It does not pay through accuracy; it pays through **power cap, PP, and rarity**. Most moves in any batch are priority `0`.

**Per-batch budget:** `≤ 7%` of moves carry elevated priority (`priority ≥ 1`). Provider themes (e.g., wind/storm/quick-strike) may justify hitting the cap; slower or grounded providers should sit well below it.

**Sparsity ladder.** Higher priority brackets are increasingly rare. Maximums below are *ceilings*, not targets — a typical batch leaves the upper rows empty.

| Priority | Use case                        | Power cap     | Real anchor                           | Per-batch ceiling |
|----------|---------------------------------|---------------|---------------------------------------|-------------------|
| `+1`     | Quick chip / jab / pre-emptive  | `≤ 40` BP     | Quick Attack (40), Mach Punch (40), Aqua Jet (40), Sucker Punch (70 — pays via conditional miss) | up to ~5% of batch |
| `+2`     | Signature mover                 | `≤ 80` BP     | Extreme Speed (80, very rare)         | ≤ ~1.5% of batch |
| `+3`     | First-turn lock-in / setup payoff | status only | Fake Out (40, only first turn — illustrative) | trace |
| `+4..+5` | Reserved control                | status only   | Quick Guard, priority blockers        | ≤ 1 per batch |
| `+6..+7` | Capstone / unique mechanic      | status only   | Pursuit-style trapping (rare canon)   | almost never |
| `0`      | Default                         | any           | most moves                            | rest of batch |
| `−1..−7` | Slow finishers / last-strike    | high power OK | Vital Throw, Trick Room moves         | trace |

**Anti-patterns:**
- Priority `≥ 1` on power `≥ 80` without a balancing drawback (self-debuff, conditional miss, recharge).
- Priority `≥ 3` on a damaging move.
- Multiple priority moves of the same type in one batch (concentrates pressure on one matchup).
- Negative priority paired with a weak power tier (the slow downside should buy a strong upside).

**Heuristic:** if you can't name the *anchor* the priority move is paying for (low power, low PP, conditional clause, status-only), it's overtuned — drop priority back to `0` or weaken another dial.

---

## 4. Type → Category: Natural Fit and When to Cross

Each type leans physical or special based on lore. Cross the lean *only* when the specific move's flavor argues for it.

| Type | Natural Category | Why | Cross-category examples (and why they cross) |
|---|---|---|---|
| **NORMAL** | Physical | Body slams, tackles | Hyper Beam (Special — beam of pure energy) |
| **FIRE** | Special | Radiant flame | Flare Blitz, Fire Punch (Physical — *contact* with the flame) |
| **WATER** | Special | Projected water | Waterfall, Aqua Tail (Physical — body contact) |
| **ELECTRIC** | Special | Discharge from distance | Wild Charge, Volt Tackle (Physical — recoil-tackle through electricity) |
| **GRASS** | Special | Spores, beams, vines from afar | Wood Hammer, Power Whip (Physical — striking with the body) |
| **ICE** | Special | Beams, blizzards | Ice Punch, Icicle Crash (Physical — strike contact) |
| **FIGHTING** | Physical | Punches, kicks | (rare; Aura Sphere is Special — energy projection) |
| **POISON** | Physical | Bites, jabs, stabs | Sludge Bomb (Special — projectile poison) |
| **GROUND** | Physical | Earthquakes, ground impacts | Earth Power (Special — energy *through* the ground) |
| **FLYING** | Physical | Wing attacks, dives | Air Slash, Hurricane (Special — air pressure projected) |
| **PSYCHIC** | Special | Mental energy | (rare; Zen Headbutt is Physical — flavor: head contact) |
| **BUG** | Physical | Stings, bites | Bug Buzz (Special — sound wave) |
| **ROCK** | Physical | Throwing/striking with rocks | Power Gem (Special — projected light) |
| **GHOST** | Physical | Strikes from spirit hands | Shadow Ball (Special — projectile orb) |
| **DRAGON** | Special | Breath, beams, pulses | Outrage, Dragon Claw (Physical — body contact) |
| **DARK** | Physical | Bites, sneak attacks | Dark Pulse (Special — radiated darkness) |
| **STEEL** | Physical | Iron Head, metal claws | Flash Cannon (Special — beam) |
| **FAIRY** | Special | Twinkles, beams | Play Rough (Physical — flavor: tackling cutely) |

**Heuristic:** if the flavor word is *project, beam, aura, breath, wave, pulse* → Special. If it's *strike, punch, slam, bite, claw, charge* → Physical. The type's natural category is just the more common flavor for that type.

---

## 5. Learnset Level Density

Where to place the **non-level-1** moves. Not every band gets equal weight — higher levels are deliberately sparse so the few moves there feel earned.

| Level range | Density | Typical power | Strategic role |
|---|---|---|---|
| Level range | Density | Typical power | Strategic role |
|---|---|---|---|
| **1** | Massive | 10–55 | Starters: chip, basic STAB, simple status |
| **2 – 15** | High | 20–60 | Setup era: stronger basic STAB, light chip, early STATUS |
| **16 – 35** | Moderate | 40–80 | Evolution window: mid STAB, battle pivots |
| **36 – 55** | Moderate | 65–100 | Core kit: Flamethrower / Ice Beam workhorse tier |
| **56 – 80** | Low | 90–120 | Finishers: high-risk / signature moves |
| **81 – 100** | Trace | 120+ | Capstones only — legendary-tone moves, very rare |

Level requirement is a battle-availability gate, not only flavor metadata. If a generated Vibemon is level 1 and its
learnset includes an 85 power move at level 1, the debug battle can legitimately become a 1-2 turn fight. Do not put
midgame or finisher power at level 1.

**STATUS moves (`power is None`)** are placed by **utility tier** (§6), not power. Lean them earlier when in doubt — keep 56–80 and 81–100 reserved.

---

## 6. Level-1 Batch Sizing (~70% target)

Most moves in any provider batch sit at level 1 (the relearner / TM-equivalent pool). For a batch of size **N**, pick `L1 ∈ 0…N` minimizing `|L1/N − 0.7|`. On ties, pick the **larger** `L1`.

The 70% L1 target does **not** license high-power L1 moves. Within level-1 damaging moves, use this distribution:

| L1 damaging power band | Share of L1 damaging moves | Notes |
|---|---:|---|
| **10–30** | 20–30% | true chip, high PP, clean damage |
| **35–45** | 45–60% | default starter attacks; reliable STAB lives here |
| **50–55** | 10–20% | strong-for-L1; usually lower PP or no rider |
| **56–60** | 0–5% | rare edge case; no strong rider |
| **>60** | 0% | not level 1 unless the user explicitly asks for overtuned/prototype moves |

For level-1 battles, target a normal matchup lasting roughly 4-6 turns, type advantage 3-4 turns, and crit/mismatch
outliers 2-3 turns. If L1 battles routinely end in 1-2 turns without crits, move power is too high for the level.

| N | Best L1 | L1 / N |
|---|---|---|
| 5 | 4 | 0.80 |
| 6 | 4 | 0.667 |
| 10 | 7 | 0.70 |
| 20 | 14 | 0.70 |
| 50 | 35 | 0.70 |

---

## 7. Level Requirement Bands

For the **non-L1** moves, soft anchors once you've picked power/utility tier (§3, §9). Align with §5: don't park ordinary moves at 80+.

| Power / Utility | Suggested level range | Real anchor |
|---|---|---|
| STATUS — light / self setup | 1–15 | Growl (L1), Leer (L1), Harden (L1) |
| STATUS — reliable control | 8–35 | Confuse Ray (L17), Toxic (L24-ish) |
| STATUS — team-defining | 36–55 | Calm Mind, Swords Dance (mid-late) |
| STATUS — fight-warping | 56–80 (rare) | Trick Room, Tailwind on signature users |
| Starter damage (10–45) | 1–15 | Tackle (L1), Ember (early) |
| Strong starter damage (50–55) | 1–20 | upper edge of L1; keep clean or lightly budgeted |
| Mid damage (60–80) | 16–45 | Flame Wheel (mid-20s), Bite (mid) |
| Strong damage (85–100) | 30–55 | Flamethrower (mid-40s on Charizard line) |
| Very strong (100–120) | 45–75 | Hydro Pump (mid-50s), Fire Blast (50s) |
| Signature / 120+ | 56–90 | Draco Meteor, Outrage (high tier) |
| Capstone (legendary tone) | 91–100 (almost never) | Reserved — most Vibemon never get here |

Hard level-power caps for normal generation:

| Level requirement | Normal max power | Rare max power | Requirements for rare max |
|---|---:|---:|---|
| **1** | 45 | 55 | no strong rider; PP/accuracy not both premium |
| **2–15** | 55 | 60 | flavor-justified, not batch-common |
| **16–35** | 75 | 80 | midgame upgrade |
| **36–55** | 95 | 100 | workhorse tier |
| **56–80** | 110 | 120 | pays with accuracy, PP, recoil, self-debuff, or similar |
| **81–100** | 120 | 150 | capstone only; major drawback for 130+ |

---

## 8. Secondary Effect Chance Standards

Two questions, in order: **(a) does the move have a rider at all?** and **(b) if so, at what chance?**

### 8a. Whether to add a rider

For **damaging moves**, the default is **no rider**. In canon Vibemon, only ~25–30% of damaging moves carry a secondary effect — the other ~70% are clean attacks whose only job is damage. Add a rider only when the theme genuinely calls for it (see §10), not as a default decoration.

**Batch target:** in any provider batch of damaging moves, aim for **~30% with riders, ~70% without**. Combined with the §6 level-1 target (~70% at L1), this means a typical 10-move batch looks roughly like: 7 at L1, 3 with secondary effects, with overlap allowed.

**Status moves are exempt** — they always have an effect because the effect *is* the move.

**User-side drawbacks don't count as riders.** Moves that lower the *user's* own stats (Overheat → –2 Sp. Atk self, Close Combat → –1 Def/Sp. Def self) are considered part of the move's cost, not a secondary effect. Don't double-count them against the 30% rider budget.

### 8b. If a rider is present, what chance?

Effect chance scales **inversely** with the move's power budget. A weak move can afford a frequent rider; a strong one cannot.

| Chance | Use case | Real anchor |
|---|---|---|
| `1.0` | STATUS moves, guaranteed-effect moves | Will-O-Wisp (100% burn), Thunder Wave (100% para) |
| `0.5` | Effect is *the move's identity* | Scald (30% burn — actually canon, but feels central) |
| `0.3` | Standard secondary on a mid-power damage move | Body Slam (30% para, 85 BP), Ice Punch (10% in canon — illustrative band) |
| `0.2` | Secondary on a powerful move | Sky Attack (30% flinch, but charged), Iron Head (30% flinch — illustrative) |
| `0.1` | Rare secondary on a high-power move | Flamethrower (10% burn, 90 BP), Ice Beam (10% freeze, 90 BP), Thunderbolt (10% para, 90 BP) |

**Heuristic:** *power tier × effect chance ≈ constant*. Flamethrower (90 × 10% burn) ≈ Ember (40 × ~25% burn implied). Don't combine 110 BP with a 30% strong-status proc — that's two heavyweight knobs at once.

---

## 9. Stat Change Conventions

| Delta | Meaning | Real anchor |
|---|---|---|
| `+1 / −1` | Single stage — common, mild | Growl (–1 Atk target), Howl (+1 Atk self) |
| `+2 / −2` | Two stages — impactful, deliberate | Swords Dance (+2 Atk self), Screech (–2 Def target) |
| `+3 / −3` | Three stages — almost never; reserved for extreme moves | Belly Drum (+6 Atk self at HP cost — outlier) |

**Multi-stat changes** are rare and signal a defining move:
- **Amnesia** — +2 Sp. Def (self).
- **Shell Smash** — +2 Atk, +2 Sp. Atk, +2 Speed, –1 Def, –1 Sp. Def (self). The downside is what makes the upside legal.
- **Sticky Web** — –1 Speed (target, on switch-in). Field-effect framing earns the persistent debuff.

---

## 10. Common Effect Combinations by Theme

| Theme | Suggested status | Suggested stat changes |
|---|---|---|
| Fire / volcanic | BURN | –1 Sp. Def (target) |
| Ice / blizzard | FREEZE | –1 Speed (target) |
| Electric / storm | PARALYSIS | –1 Speed or –1 Accuracy (target) |
| Toxic / poison | POISON or BAD_POISON | –1 Defense (target) |
| Sleep / dream | SLEEP | — |
| Dark / shadow | — | –1 Accuracy or –1 Sp. Def (target) |
| Fighting / force | — | +1 Atk self, –1 Def target |
| Psychic / mind | — or PARALYSIS | –2 Sp. Def or –1 Speed (target) |
| Rock / earth | — | –1 Speed (target) |
| Fairy / enchant | — or SLEEP | –2 Atk (target) |

---

## 11. Worked Examples (end-to-end)

These show every dial resolving together. Trace the reasoning column to internalize the flow.

### Example A — "Flamethrower" (fire workhorse)

| Dial | Value | Reasoning |
|---|---|---|
| Type | FIRE | Theme: focused jet of flame |
| Category | Special | FIRE's natural category; flame projected, not contact |
| Power | 90 | "Workhorse" tier (§3 row 80–100) |
| Accuracy | 100% | Top of the band — this is the *reliable* fire move |
| PP | 15 | Mid of the 10–15 band; signals everyday use |
| Level requirement | mid-40s for fire-line learners; **L1** if dropped into the relearner pool | §7 strong-damage row; matches Charizard-line canon |
| Secondary | 10% BURN | §8: high power → low chance; theme→burn (§10) |

Sanity check: power 90 + 100% acc + 15 PP + 10% burn — none of the dials maxed simultaneously. ✅

### Example B — "Focus Blast" (fighting signature)

| Dial | Value | Reasoning |
|---|---|---|
| Type | FIGHTING | Theme: explosive martial energy |
| Category | Special | Crosses FIGHTING's natural physical lean — flavor justifies (focused *energy*, not a punch) |
| Power | 120 | Signature tier (§3 row 110–120) |
| Accuracy | 70% | Pays for power |
| PP | 5 | Pays for power |
| Level requirement | 55–70 | §7 very-strong band |
| Secondary | 10% –1 Sp. Def | Low chance; matches §8 for power tier |

Sanity check: 120 power demands a drawback — accuracy 70% *and* 5 PP delivers it. ✅

### Example C — "Will-O-Wisp" (utility)

| Dial | Value | Reasoning |
|---|---|---|
| Type | FIRE | Theme: ghostly flame curse |
| Category | Status | Pure utility |
| Power | None | Status |
| Accuracy | 85% | High-utility status moves trade 100% for impact |
| PP | 15 | §6 "reliable condition" tier |
| Level requirement | L1 (relearner) or 16–35 if natural-learn | §7 STATUS reliable-control band |
| Effect | 100% BURN on hit | Status moves get `1.0` chance (§8) |

Sanity check: a 100% burn at 100% accuracy would dominate; 85% accuracy is the cost. ✅

### Example D — "Vine Whip" (early-game STAB)

| Dial | Value | Reasoning |
|---|---|---|
| Type | GRASS | Theme: quick lash with a vine |
| Category | Physical | Crosses GRASS's natural special lean — flavor: contact strike |
| Power | 45 | Chip / early-STAB tier (§3) |
| Accuracy | 100% | Cheap moves should hit (logic check) |
| PP | 25 | High PP; spammable |
| Level requirement | L1 or 5–10 | §7 weak-damage band |
| Secondary | none | Cheap moves rarely carry riders |

Sanity check: nothing remarkable on any dial — exactly what an early-game move should look like. ✅

---

## 12. Anti-Pattern Checklist (run before finalizing)

If any of these are true, the move is overtuned — weaken a dial.

- [ ] Power ≥ 100 **and** accuracy = 100% **and** PP ≥ 15
- [ ] Power ≥ 120 with no drawback (acc penalty / recharge / recoil / 5 PP / self-debuff)
- [ ] Power ≥ 100 with a ≥ 30% strong-status proc (paralysis / burn / freeze / sleep)
- [ ] Status move with 100% accuracy that inflicts SLEEP or FREEZE (these always trade accuracy)
- [ ] Move below level 15 raises evasion or lowers target accuracy
- [ ] +2 stat change paired with damage and no downside
- [ ] Sub-60 power move with accuracy under 100% (no flavor reason to miss)
- [ ] 5 PP on a move under 90 power and without a heavy effect
- [ ] Crossed type→category without a flavor reason (a "Special FIGHTING punch" or "Physical PSYCHIC beam")
- [ ] Common move parked in the 56–80 or 81–100 level band
- [ ] Level 1 damaging move above 55 power
- [ ] Level 1 damaging pool has too many 50-55 power moves (>20% of L1 damaging moves)
- [ ] Batch's L1 ratio drifted outside `|L1/N − 0.7| ≤ 0.05` (HARD)
- [ ] Any single type's L1 share drifted more than `±15pp` from the batch L1 ratio
- [ ] Batch's damaging-move rider ratio drifted far from ~30% (most common drift: too many riders, making every move feel "loaded")
- [ ] A damaging move has a rider with no thematic justification — added "because riders are interesting" rather than because the theme demanded it
- [ ] Power-band distribution: any tier below 50% of §3.5 target, or any tier exceeding 40% of damaging moves
- [ ] No capstone (power ≥ 120) anywhere in the batch
- [ ] Elevated priority (`priority ≥ 1`) exceeds 7% of the batch
- [ ] Priority ≥ 1 on power ≥ 80 without a balancing drawback, or priority ≥ 3 on a damaging move

---

## 3.7. Sure-Hit Budget (`accuracy=None`)

Moves with `accuracy=None` (Sure-Hit) bypass accuracy and evasion checks. This is a powerful trait that must be budgeted tightly.

**Per-batch budget:** `≤ 5%` of total moves.

**Justification:** Only for moves themed around:
- Homing / Tracking (Radar Jolt)
- Aura projection / Mental lock-in (Aura Sphere)
- Unavoidable field conditions (Cinder Draft, if themed as a wide area effect)
- Magic / Fae trickery (Prism Breeze)

**Default**: `accuracy=1.0` is the standard for reliable moves. Use `None` only when the fantasy *demands* it.
