# Plan 06 — Landmarks and page structure

**Findings:** A11Y-006  
**Severity:** Medium  
**Effort:** S (half day)  
**Primary files:**

- `vibemon/frontend/src/routes/+layout.svelte`
- `vibemon/frontend/src/lib/ui/SceneFrame.svelte`
- Route pages: `battle/[id]/+page.svelte`, `deck/crew/+page.svelte`, `hatch/+page.svelte`, `register/+page.svelte`, `login/+page.svelte`, `encounters/+page.svelte`

---

## Goal

Screen reader and keyboard users can:

1. **Skip** repetitive chrome (cabinet bezel, settings knob) to primary content.
2. Navigate by **landmarks** (`main`, `nav` where appropriate).
3. Encounter a sensible **heading hierarchy** per route.

---

## Current state

| Route | `<main>` | `<h1>` | Notes |
| :--- | :--- | :--- | :--- |
| `/` (title) | No | Yes (`TitleScene`) | `nav` with title menu — good |
| `/styleguide` | Yes | Yes | Reference implementation |
| `/battle/{id}` | No | No | Full-screen scene |
| `/deck/crew` | No | No | |
| `/register`, `/login` | No | Partial | Scenes inside layouts |

`SceneFrame` wraps most game UI but is a `<div>` without landmark role.

---

## Implementation

### Step 1 — Skip link in root layout

`src/routes/+layout.svelte`:

```svelte
<a href="#main-content" class="skip-link">Skip to game</a>
…
<div id="main-content">
  {@render children()}
</div>
```

Styles in `app.css`:

```css
.skip-link {
  position: absolute;
  left: -9999px;
  z-index: 10000;
  padding: var(--vm-space-sm) var(--vm-space-md);
  background: var(--vm-parchment);
  color: var(--vm-tobacco-black);
  font-family: var(--vm-font-ui);
}
.skip-link:focus {
  left: var(--vm-space-md);
  top: var(--vm-space-md);
  outline: 2px solid var(--vm-mustard);
}
```

Skip target `#main-content` wraps `{@render children()}` — not inside `SceneFrame` so it skips bezel chrome when frame is child.

### Step 2 — `SceneFrame` documents structure

Add optional prop:

```typescript
mainLabel?: string; // e.g. "Battle", "Crew roster"
```

When set, wrap `{@render children()}` overlay:

```svelte
<main class="scene-frame__main" aria-label={mainLabel}>
  {@render children()}
</main>
```

Default: `main` without label if only one main per page.

**Do not** nest multiple `<main>` — each route should have at most one. If layout adds `#main-content`, SceneFrame inner wrapper can be `<div role="region" aria-label={mainLabel}>` instead to avoid double-main.

**Recommended structure:**

```
+layout: skip link + #main-content (div)
  +page: SceneFrame
    div.scene-frame__overlay
      main.scene-frame__main[aria-label]
        scene content
```

Update `+layout.svelte`:

```svelte
<main id="main-content" class="app-main">
  {@render children()}
</main>
```

SceneFrame uses `role="region"` + `aria-label` on overlay when `mainLabel` passed — avoids invalid nested mains.

### Step 3 — Per-route labels

| Route | `mainLabel` / heading |
| :--- | :--- |
| Battle | `"Battle"` + visually hidden h1 optional |
| Crew | `"Crew"` |
| Hatch | `"Hatch"` |
| Register | `"Register trainer"` |
| Login | `"Login"` |
| Encounters | `"Encounters"` |
| Title | `"Vibemon title"` — h1 already visible |

Example battle page:

```svelte
<SceneFrame … mainLabel="Battle">
  <h1 class="sr-only">Battle</h1>
  <BattleScene … />
</SceneFrame>
```

Reuse `.sr-only` from Plan 05.

### Step 4 — Title scene

Already has `<h1>Vibemon</h1>` and `<nav aria-label="Title menu">`. No change beyond layout skip link.

### Step 5 — Settings / Guide knobs

Remain outside `main` (part of SceneFrame chrome) — skip link jumps past them into scene content. Knobs stay focusable after skip.

---

## CSS

Ensure `.app-main` does not break layout:

```css
.app-main {
  min-height: 100vh;
  display: contents; /* if wrapper must not affect flex — test; else block */
}
```

`display: contents` removes box from a11y tree in some browsers — **avoid** if it hides main landmark. Prefer:

```css
.app-main {
  min-height: 100vh;
}
```

---

## Tests

### Manual

1. Load `/` → Tab once → skip link visible → Enter → focus moves to title menu or main content.
2. VoiceOver rotor → Landmarks → one main / region per page.
3. Headings menu lists h1 on battle (sr-only) + visible scene headings where applicable.

### Automated (Plan 11)

axe: `landmark-one-main`, `page-has-heading-one` on `/battle/*` stub.

---

## Acceptance criteria

- [ ] Skip link on all routes via root layout.
- [ ] Single primary landmark per page (`main` in layout OR labeled region in SceneFrame — documented choice, not both nested incorrectly).
- [ ] Battle and crew routes expose h1 (visible or sr-only).
- [ ] No layout regression on mobile portrait.
- [ ] `pnpm check` passes.

---

## Non-goals

- Restructuring entire route hierarchy.
- Breadcrumb navigation.
