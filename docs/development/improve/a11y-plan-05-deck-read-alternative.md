# Plan 05 — Deck Read accessible alternative

**Findings:** A11Y-005  
**Severity:** High  
**Effort:** L (3–5 days — UX + design touch)  
**Depends on:** Plan 04 (battle HUD/menu focus stable)  
**Primary files:**

- `vibemon/frontend/src/lib/domains/battle/BattleScene.svelte`
- `vibemon/frontend/src/lib/domains/battle/BattleHudPlate.svelte`
- `vibemon/frontend/src/lib/domains/battle/MoveMenu.svelte`
- `vibemon/frontend/src/lib/domains/battle/battleSession.svelte.ts` (if persisting toggle state)
- `docs/development/DESIGN.md` §9.2

---

## Goal

Deck Read (`docs/development/DESIGN.md` §9.2) exposes extra battle information while held:

| Surface | Baseline | While Deck Read active |
| :--- | :--- | :--- |
| Combatant HUD | Name, Lv, HP, XP | Stat stages, status counters, XP-to-next |
| Move menu | PP, power, accuracy, type | Effectiveness copy per tile + highlighted move read |

Today activation is **`hold C`** only (`contextHeld` in `BattleScene`). `DESIGN.md` states: *"Keyboard-only this slice."*

Accessible alternative must serve:

- **Touch / mobile** — no keyboard hold.
- **Screen reader users** — cannot perceive visual-only reveals.
- **Motor** — holding a key while navigating is awkward.
- **Sticky toggle** — optional for users who cannot hold.

---

## UX proposal (recommended)

### Toggle: "Read" mode

Add a **Read** control to battle footer (near dialog or as tertiary `GameButton`):

- Label: **Read** / **Reading** (or icon + `aria-label="Toggle detailed readout"`).
- `aria-pressed={contextHeld}` on a real `<button>`.
- Click toggles `contextHeld` (sticky); keyboard **`C`** still sets held while key down (existing) **or** migrate to toggle-only for simplicity.

**Design doc update:** §9.2 becomes *"Deck Read (toggle or hold C)"* with touch path documented.

### Live region for readout text

When `contextHeld && readLine` in move menu, mirror text to:

```svelte
<div class="sr-only" aria-live="polite" aria-atomic="true">
  {readLine}{effectivenessLine ? ` ${effectivenessLine}` : ''}
</div>
```

Add utility class in `app.css`:

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

Same for HUD stat-stage block when context active — announce stage deltas when toggled on.

### Hint in dialog / first battle

First wild battle or help toast: *"Tap Read for move matchups and stat details."* — use `showGameToast` once per session flag in `sessionStorage`.

---

## State model

### Current

```typescript
let contextHeld = $state(false);
// keydown C → true, keyup C → false
```

### Target

```typescript
let deckReadActive = $state(false); // sticky toggle
let deckReadHeld = $state(false);   // C key transient

let contextHeld = $derived(deckReadActive || deckReadHeld);
```

Or single `deckReadActive` if dropping hold-C ( simpler — discuss with design).

**Recommendation:** Keep hold-C **and** add toggle; both OR into `contextHeld`.

---

## UI placement options

| Option | Location | Pros |
| :--- | :--- | :--- |
| **A** | Footer bar left of dialog | Always visible |
| **B** | Inside `MoveMenu` stats panel header | Contextual |
| **C** | Cabinet guide meta slot via `SceneFrame` `meta` snippet | Reuses guide rail |

**Pick A** for discoverability — small tertiary button in `battle-scene__footer`.

Mockup spec (no Figma required):

- `GameButton variant="tertiary"`
- `aria-pressed={contextHeld}`
- Visible label: `Read`
- When active, `--vm-mustard` outline on button (reuse selected styling)

---

## `MoveMenu.svelte` changes

Already computes:

```typescript
let readLine = $derived(highlighted && contextHeld ? moveReadHint(highlighted) : null);
let effectivenessLine = $derived(...);
```

Add visible **read block** when `contextHeld` (already shown). Ensure content is **not** `aria-hidden`.

Add screen-reader-only live mirror (above).

When `contextHeld` false, effectiveness glyphs on tiles hidden — OK.

---

## `BattleHudPlate.svelte` changes

Stage block:

```svelte
{#if contextHeld}
  <div class="battle-hud__context" aria-live="polite">
```

Already has `aria-live="polite"`. Verify toggling Read announces stage list — may need `aria-atomic="true"` or brief delay on toggle.

Add **XP to next** text line when Read active (per DESIGN §9.2) if not already rendered.

---

## Mobile / touch

Toggle button meets 44px touch target via `GameButton`.

Remove dependency on hover for any Deck Read content (already key-gated).

---

## Documentation

Update `docs/development/DESIGN.md` §9.2 table footnote:

```markdown
**Activation:** Hold `C` (desktop) or tap **Read** (all platforms). Read mode is sticky until toggled off.
```

Update battle-screen plans if they reference hold-C only.

---

## Tests

### Manual

1. Battle → move select → tap Read → effectiveness text visible + announced in NVDA.
2. Hold C → same state as Read on (if dual path kept).
3. Release C with toggle off → returns to baseline.
4. Toggle on → navigate moves with arrows → live region updates.
5. Portrait mobile layout → Read button reachable.

### Automated

`battleSession.test.ts`: `contextHeld` derived from toggle helper.

---

## Acceptance criteria

- [ ] Non-keyboard path enables Deck Read (toggle button minimum).
- [ ] `aria-pressed` reflects Read state.
- [ ] Move read + effectiveness exposed to screen readers (`aria-live` or visible text).
- [ ] HUD extended stats announced when Read enabled.
- [ ] `DESIGN.md` §9.2 updated.
- [ ] No regression to arrow-key battle navigation.

---

## Non-goals

- Remapping C to other keys.
- Gamepad button for Read (future).
