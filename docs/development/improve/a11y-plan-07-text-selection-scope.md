# Plan 07 — Text selection scope

**Findings:** A11Y-007  
**Severity:** High (for users who copy text, use magnifiers, or assistive tech that depends on selection)  
**Effort:** S (1–2 hours)  
**Primary files:**

- `vibemon/frontend/src/app.css`
- Possibly component-level overrides for story/dialog panels

---

## Goal

Remove the **global** selection block; restrict `user-select: none` to game chrome where dragging would confuse gameplay (sprites, buttons during drag, cabinet bezel).

**Readable/copyable:** dialog text, story entries, error toasts, form inputs, guide readout hints, registration copy.

---

## Current rule

```12:18:vibemon/frontend/src/app.css
*,
*::before,
*::after {
  box-sizing: border-box;
  user-select: none;
  -webkit-user-select: none;
}
```

This applies to **every** element including `<p>`, `<input>` (inputs often still allow selection of value — but story paragraphs cannot).

---

## Implementation

### Step 1 — Narrow global reset

Replace universal rule with:

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}

/* Default: allow selection on text content */
body {
  margin: 0;
  min-height: 100vh;
  user-select: text;
  -webkit-user-select: text;
}

/* Game chrome: prevent accidental selection during play */
.scene-frame,
.scene-frame *,
.game-button,
.free-form-button,
.command-menu__cell,
.move-menu__cell,
.crew-formation-menu__cell,
.battle-mon__model,
img,
canvas {
  user-select: none;
  -webkit-user-select: none;
}

/* Explicit copy-friendly regions */
.dialog-box__text,
.crew-showcase-panel__story-body,
.hatch-candidate-panel__empty,
.game-toast__text,
.mobile-viewport-guide__body,
.trainer-name-input__native {
  user-select: text;
  -webkit-user-select: text;
}
```

### Step 2 — Audit copy-heavy surfaces

Grep for class names on long text:

```bash
rg 'story-body|dialog-box|__body|__read' vibemon/frontend/src --glob '*.svelte'
```

Add `user-select: text` to any missed prose containers:

- Provider config descriptions
- Hatch candidate hints in guide panel (if rendered as text node)

### Step 3 — Inputs

Native `<input>` / `<textarea>` inherit text selection — ensure they are not inside a `user-select: none` parent without override. `TrainerNameInput` native input already has override in list above.

### Step 4 — Buttons

Keep `user-select: none` on buttons — selecting label text inside buttons is rarely needed.

---

## Interaction with drag gestures

If crew formation or hatch uses pointer drag on sprites, localized `user-select: none` on those containers prevents highlight flash — already covered by scene-frame / sprite rules.

---

## Tests

### Manual

1. Battle dialog resolving — drag-select words in dialog → selection highlight appears.
2. Crew story tab — select paragraph text → copy to clipboard works.
3. Toast message — selectable.
4. Command menu buttons — still no accidental text selection on rapid clicks.

### Automated

None required — visual/CSS change.

---

## Acceptance criteria

- [ ] Global `*` no longer sets `user-select: none`.
- [ ] Dialog and story prose selectable.
- [ ] Game controls/sprites do not show selection highlight on click-drag.
- [ ] No regression reported on mobile long-press (context menu may appear on story text — acceptable).

---

## Non-goals

- Context menu customization.
- `::selection` color theming (optional polish — mustard highlight could match brand).
