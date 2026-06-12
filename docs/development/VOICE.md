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
