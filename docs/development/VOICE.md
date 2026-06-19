# Vibemon Voice

Quick reference for player-facing copy, flavor text, and generated prose. Full aesthetic vision: `DESIGN.md`. Canonical terms: `CONTEXT.md`. Capture gear strings: `GEAR.md` §Player-Facing Copy.

## Register

Vibemon speaks like a **cozy mid-century field journal** — warm, unhurried, tactile, a little analog. The world runs on decks, carts, reels, and signals, not apps and dashboards. Copy should feel like guidance from a patient friend on a long walk, not a product onboarding flow.

**Feeling keywords:** cozy, warm, gentle, playful, unhurried, tactile, sincere.

**Not this:** edgy, snarky, urgent, meta, parody, startup-speak, franchise mimicry.

## Tone Guardrails

From the design and audio direction (`DESIGN.md` §1, §7.4):

- **Warmth over tension.** Even warnings stay calm — never alarmist or punitive.
- **Playful, not comedic.** Whimsy is fine; jokes, irony, and winking meta humor are not.
- **Space over density.** Short sentences. One idea per line in UI. Let copy breathe.
- **Sincere, not sarcastic.** The cozy register is earnest; don't undercut it.
- **Unhurried.** No FOMO, countdown pressure, or "Act now!" energy.
- **Journey, not punishment.** Release, expiration, and missed opportunities read as part of the path — never scolding.

## Sentence Shape

- **UI labels & buttons:** 1–4 words when possible. Stay consistent within a screen (Title Case or sentence case — pick one per context).
- **Hints & tooltips:** One or two short sentences. Plain, direct.
- **No em dashes in player copy.** Use periods, commas, or a gentle colon instead. Break ideas into short sentences rather than chaining clauses with `—`.
- **Suspense / loading beats:** Sensory, gentle, present tense. Analog texture welcome (*static whispers*, *the glow gets a touch warmer*).
- **Errors & warnings:** State what happened and what to do next. No blame. Prefer **warning** over **error** when non-fatal (`Provider Warning` semantics — see `CONTEXT.md`).

## Do / Don't

| Prefer | Avoid |
| :--- | :--- |
| *The shell gives a little shake...* | *Loading your Vibemon...* |
| *Almost there, Trainer...* | *Hang tight! We're almost done!* |
| *Welcome them to your crew* | *Unlock your first crew member!* |
| *Release them to the Wild* | *Delete this Vibemon* |
| *Cart saved!* / *Vibe recorded!* | *Gotcha!* / *Caught!* |
| *Keep at least one vibe source connected.* | *Error: no providers selected.* |
| *Signal lost* | *Capture failed — try again!* |
| *Finish vibe source setup before you connect it.* | *Complete onboarding to continue.* |

## Vocabulary

Use **canonical domain terms** — never franchise leakage or generic substitutes. Full glossary: `CONTEXT.md`.

| Concept | Use | Avoid |
| :--- | :--- | :--- |
| Player character | **Trainer** | player (in UI), user |
| Active roster | **Crew** | party, team, box |
| Field device | **Vibe Deck** | Pokédex, bag, phone |
| Storage medium | **Vibe Cart**, **Cart** | ball, cartridge (in UI) |
| Birth flow | **Hatch**, **Generation** | spawn, mint |
| Wild capture | **Press**, **Slot Cart** | throw, trap |
| Leave roster | **Release** (to **Wild**) | delete, discard |
| Non-fatal issue | **Warning**, gentle note | error, failure |
| Battle: open moves | **Moves** | Fight |
| Battle: field device | **Deck** | Bag, items |
| Battle: swap member | **Crew** | Vibemon, Party, Switch |
| Battle: leave encounter | **Run** | flee, escape |
| Experience track | **XP** | EXP, exp |
| Level up | **grew to Lv {n}** | leveled up, gained a level |

## Battle Command Menu

The four-way command menu keeps the canonical 2×2 *shape* but uses Vibemon's own language, never franchise labels:

```
MOVES   DECK
CREW    RUN
```

- **MOVES** — opens the active Vibemon's move list. (Not "Fight" — VOICE bans franchise mimicry.)
- **DECK** — the **Vibe Deck** (items, **Press** capture). (Not "Bag" — `CONTEXT.md` bans it.)
- **CREW** — swap the active **Crew** member. (Not "Vibemon"/"Party".)
- **RUN** — leave a **Wild** encounter.

A slot with no shipped behavior renders **shown-but-greyed**, not removed — the empty slot signals depth that is coming, in keeping with "Journey, not punishment."

## Battle HUD & Progression

- **HP** and **XP** are the two stacked plate labels — both two letters so they align in the molded-gauge readout. ("XP" not "EXP"; the code field is `xp`, the player label is XP.)
- The **XP bar fills silently** — no spoken number callout (VOICE: no stat references in player-facing prose).
- **Level-up** is the only progression line spoken: *"{name} grew to Lv {n}!"* ("grew" reads organic and cozy, not mechanical).
- Reserve for later (out of scope now): *"{name} is ready to learn a new move."*

## Battle Beats (Wild Encounter)

There is no wild *trainer* — only a lone **Wild** Vibemon. Copy never implies an opposing trainer. Register stays cozy and unhurried; wins get no fanfare, defeat gets no blame.

| Beat | Copy |
| :--- | :--- |
| Encounter reveal | *A wild {name} steps out.* |
| Send out member | *Go, {name}!* |
| Opponent faints (win) | *The wild {name} faints.* |
| Your member faints | *{name} faints.* |
| Battle won | *(silent — proceed straight to XP / level-up)* |
| **Defeat** (no **Crew** left) | *You and your crew head home to rest.* |
| Run | *You slip away.* |

- **Faint** keeps the mainline word — gentle, understood, backed by the record-winding-down faint SFX (`DESIGN.md` §7.3). Do not coin a cozier synonym; it would muddy a core concept.
- **Defeat** copy follows "Journey, not punishment" — never *"You lost"*, *"whited out"*, or *"Game over."*

## Deck Read (hold-C hidden depth)

Holding **C** consults the **Vibe Deck** to reveal hidden depth; releasing returns to the resting screen. On-screen hint: *Hold C — Read*.

- **Baseline** (always visible, canonical): HP + exact HP numbers, XP bar, and each move's PP / power / accuracy / type.
- **Deck Read** (held) adds only the hidden depth: stat-stage arrows (non-zero only), status/volatile **turn counters**, *XP to Lv {n}*, and per-move **effectiveness**.
- **Effectiveness** shows as glyph + tint on every move tile; the highlighted move also spells the phrase: *Super effective* / *Not very effective* / *No effect*. Keep these three phrases exact — no "It's super effective!" franchise punctuation.

Capture-specific preferred strings: `GEAR.md` §Player-Facing Copy.

## Hatch review panel

Evolution-line copy uses **Stage** (never Form). The hatchling is always stage 1 of its line.

| Situation | Header | Stats subtitle |
| :--- | :--- | :--- |
| Single-stage species | **Single-stage** | *No evolutions ahead* |
| 2-stage line | **Stage 1 of 2** | *2-stage evolution line* |
| 3-stage line | **Stage 1 of 3** | *3-stage evolution line* |
| Deep line (pseudo-legendary seed) | **Stage 1 of 3** | *Deep evolution line* |

Avoid "pseudo-legendary" in player copy — the ✦ pip carries rarity.

**EVO hover hints** (ledger, one or two short sentences; use **Stage**, never Form):

| Situation | Example hint |
| :--- | :--- |
| Single-stage | *Sproutling has no evolutions ahead.* |
| Stage 1 of 2 | *Sproutling is at stage 1. One more evolution ahead.* |
| Stage 1 of 3 | *Sproutling is at stage 1. Two more evolutions ahead.* |
| Mid-stage | *Sproutling is at stage 2. One more evolution ahead.* |
| Fully evolved | *Sproutling is fully evolved.* |
| Deep line | Append: *A deep evolution line. Rarer and stronger than most three-stage paths.* |

Provider column on `/hatch` is **signal inputs** / **vibe sources** (patch panel), never "carts."

## Provider Warnings & Soft Failures

When a birth completes with thin inputs, the tone is **informative and reassuring**, not alarming.

- Say what was partial and that the Vibemon still arrived.
- Skip technical jargon unless the screen is explicitly diagnostic.
- Never imply the Trainer did something wrong.

## Generated Copy (GenAI)

Battle cries, species names, move flavor, and similar generated text should match this register. Structural rules live in prompt templates under `vibemon/backend/app/genai/prompts/`; tone defaults live here.

- **Species names:** coined, pronounceable, tier-weighted — not puns or real English compounds.
- **Flavor text:** evocative and type-aware; short; no stat references in player-facing prose.
- **Battle cries:** sensory and analog-digital texture; energetic but not harsh.

## Related Docs

| Doc | Role |
| :--- | :--- |
| `DESIGN.md` | Full visual, animation, and audio aesthetic |
| `COLORS.md` | Locked palette quick reference |
| `CONTEXT.md` | Domain vocabulary and term boundaries |
| `GEAR.md` | Gear visuals and capture copy table |
