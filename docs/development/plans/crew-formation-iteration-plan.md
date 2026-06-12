# Crew Formation ("Perspective Ring") — Iteration Plan

| | |
| --- | --- |
| **Status** | Plan |
| **Related** | [../ideas/mon-event-history.md](../ideas/mon-event-history.md) |
| **Scope** | `/deck/crew` — `CrewFormationScene`, `CrewClockFormation`, `CrewMemberPanel` |
| **Goal** | Cozy + "wow moment": whole crew at once, spin into view, full party management, showcase, timeline avenue |
| **References** | `DESIGN.md`, `/hatch` (`TrainerConfigurationScene`, `HatchCandidatePanel`), `/register` (`TrainerRegistrationScene`) |

## Assessment of current screen

What works — keep:

- Ring-as-clock metaphor with trainer at the hub. Diegetic, original, scales to 6.
- Quantized rotation (`steps(8)` per 60° tick) — already DESIGN.md §6.1 compliant. Position snaps, scale follows live tween: correct split.
- Honest species heights via `trainerRelativeHeight` against the trainer yardstick.
- Mirror-only facing (no sprite rotation), `mod`-based shortest-path rotation.
- `HatchCandidatePanel` reuse with `showActions={false}`.

What violates DESIGN.md or undercuts the moment:

1. **Depth via blur** — `depthBlur()` + `filter: blur()` on benched/empty sprites. DESIGN.md §4 is explicit: depth through *palette and contrast, never blur*; §1 forbids soft-focus. This is the single biggest style break.
2. **Empty slots render as black silhouettes** (`brightness(0)` on the hatchling placeholder). Reads as an unrevealed/mystery mon, not an open seat — actively misleading (screenshot slots 2–3 look like creepy shadow mons).
3. **Flat, sterile stage.** One green gradient ellipse on a banded background. DESIGN.md §4 wants layered pixel parallax (tree-lines in Sage Olive / Olive Drab), warm vignette, light grain. `/hatch` already has `HatchSceneDepth` and `FilmGrain` doing this work; the crew scene has none of it. This is where "cozy" is lost.
4. **Three stacked boxes top-left** (HP plate, position chips, candidate panel) read as floating debug UI, not a composed scene. The HP plate duplicates data the candidate panel could own. The "Lead 2 3 4 5 6" chips read as nav tabs, not seat positions.
5. **No arrival choreography.** Screen loads with the ring already settled — the one free "wow" (your whole crew assembling) is unspent.
6. **No audio.** §7.3 maps directly: rotary-dial tick per 60° advance, soft thunk on seat-swap commit.
7. **Move interaction is abstract.** Position chips move the active mon by label. Functional, but the canonical party-screen feel is *direct*: pick a mon, pick a destination seat, watch them trade places.

## Plan

### Phase 1 — Design-language compliance (style)

1. **Replace blur with palette depth.** Delete `depthBlur`/`--depth-blur`. Benched mons get atmospheric perspective per §4: keep current `brightness(0.82) saturate(0.78)`, add a cool shift (e.g. slight hue toward Slate Sky via `filter` or a tobacco-tinted overlay), scaled by the same `spotlightFactor`. Back-of-ring mons sit cooler and more muted; spotlight mon at full palette warmth. Crisp edges everywhere.
2. **Empty seats read as empty.** Drop the darkened silhouette. Render the seat platform alone — fainter disc, dashed/dithered rim in Tobacco Brown 30%, slot number, and on tap the existing hint plus a small `Hatch` affordance routing to `/hatch`. An open seat is an invitation, not a ghost.
3. **Stage atmosphere.** Bring the scene up to `/hatch` parity: layered tree-line silhouette bands (Sage Olive / Olive Drab) behind the ring via `HatchSceneDepth` or a sibling, warm vignette + `FilmGrain` as screen-space post over the frame (§4 — never on sprites). The ring ellipse stays; give it a subtle dither texture instead of the smooth radial gradient (§2.2 dither note applies to large fills too).
4. **Consolidate the left column into one panel.** Fold the `CrewMemberPanel` HP plate into `HatchCandidatePanel`'s header region for this context (name / types / Lv / HP bar together — the §3.2 segmented-block HP treatment, not the smooth fill currently in `CrewMemberPanel`). One panel, one silhouette, anchored like the hatch screen's candidate review. Per the iteration framing: fine to do this with a crew-specific header slot rather than generalizing the panel.

### Phase 2 — The wow moment (arrival + motion + sound)

5. **Assembly choreography on mount.** Trainer fades in at the hub first; mons hop onto their seats one at a time clockwise from Lead (staggered ~150ms, `steps()` hop with volume-conserving squash on landing, §6.1). Then the ring does one full 360° spin-in (6 ticks) settling on Lead. Respect `prefersReducedMotion` (already wired) — reduced motion = instant settle. First visit gets the full ritual; subsequent visits a shortened version (hop-in only).
6. **Spotlight greet.** When a mon lands in the 5:00 spotlight, one small acknowledgment: a single hop or squash-stretch pulse + nameplate pop to mustard. Cheap, sells "this one is looking at you."
7. **Audio per §7.3.** Rotary-dial/typewriter tick on each 60° advance (menu-navigation sound), warm blip on spotlight settle, plastic thunk on swap commit. The ring *is* a dial — the rotary reference is literal here.
8. **Idle life.** Benched mons get the slow `idle-breathe` loop (§6.3); spotlight mon a slightly larger amplitude. Stagger phases so the ring doesn't breathe in unison.

### Phase 3 — Party management (canonical party-screen functionality)

9. **Direct seat-swap mode.** Keep position chips as the fast path, but add the canonical flow: with a mon in the spotlight, a `Move` action enters swap mode — seat platforms light up as drop targets, tapping a seat swaps. Dialogue box narrates ("Where should FESALI stand?"). Escape cancels.
10. **Animate the swap.** On swap, both mons hop across the ring to their new seats (stepped arc, ~0.6s) instead of teleporting via rotation arithmetic. The optimistic-update + rollback logic in `moveActiveToSlot` stays; only presentation changes.
11. **Keyboard/gamepad completeness.** Arrows rotate (exists); add `1`–`6` to jump a seat to front, `Enter` to open showcase/move menu on the spotlight mon, `M` for move mode. Touch targets already on the UI layer per §5.4.

### Phase 4 — Showcase + timeline avenue

12. **Showcase is this screen, not a second screen.** The spotlight + consolidated panel *is* the Pokémon "Summary" page, surfaced inline — this is the screen's structural advantage over the canonical design. Lean in: when not in move mode, the panel is the showcase.
13. **Timeline tab.** Add a fourth tab to the panel — `Stats / Moves / Sources / Story` — rendering the mon-event-history ledger chronologically (birth → adoption → battles → level-ups), player-facing events only (`rebalance` filtered, per the idea doc). Until the ledger ships, stub it from what exists today: BirthSnapshot (birth: provider, date) + adoption record. Two real entries beat an empty state, and it establishes the UI slot the ledger will fill — matching the idea doc's "Timeline UI last, once a few event types exist."
14. **Voice pass.** Dialogue lines through `VOICE.md` register — "Your crew gathers." on assembly, seat-swap confirmations, empty-seat invitation copy.

## Sequencing & risk

- Phase 1 is pure CSS/markup, low risk, biggest cozy payoff per hour. Do first.
- Phase 2 items 5–6 touch `CrewClockFormation` placement math; the hop-in can reuse the existing tween infra (per-slot delay on a shared progress). Audio (7) depends on whether the SFX pipeline exists yet — if not, ship choreography silent and leave hooks.
- Phase 3 item 10 (swap arc) is the hardest animation; ship 9 (mode + instant swap with platform highlights) first, arc as a follow-up.
- Phase 4 item 13 needs a small backend read endpoint only if stubbing beyond BirthSnapshot; keep it frontend-only initially.

## Non-goals (this iteration)

- Generalizing `HatchCandidatePanel` into a reusable mon-detail component — crew-specific header slot is fine.
- The full event-ledger backend (`vibemon_event` table) — the Story tab stubs from existing data.
- Roster grid view changes (`/deck/crew/roster`) — separate surface.
