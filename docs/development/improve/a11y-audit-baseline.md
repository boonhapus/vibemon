# Accessibility audit baseline

**Date:** 2026-06-18  
**Scope:** `vibemon/frontend` (Svelte 5, static adapter)  
**Method:** Static code review, `pnpm check`, grep for ARIA/focus/keyboard patterns, cross-read with `DESIGN.md`.

This document is the canonical snapshot of accessibility posture **before** the fix plans in this directory land. Update the scorecard when a plan ships.

---

## Executive summary

The frontend is **game-first with thoughtful component-level accessibility**. Core primitives (`GameButton`, `FreeFormButton`, `DialogBox`, `GameModal`, HP/XP bars) include labels, focus rings, and live regions where it matters. Battle and title flows support arrow-key + confirm navigation.

Gaps cluster around **incomplete ARIA widget patterns** (tabs, menus), **dual input models** (window keys vs focusable buttons), **keyboard-only Deck Read**, **modal focus management**, and **global CSS that blocks text selection**. There is **no automated a11y test pipeline** beyond Svelte compiler checks.

`svelte-check` reports **0 errors, 0 warnings** at audit time.

---

## Scorecard

| Area | Rating | Evidence |
| :--- | :--- | :--- |
| Keyboard — game flows | Good | `BattleScene.svelte`, `TitleScene.svelte`, `CrewFormationScene.svelte`, `DialogBox.svelte` |
| Keyboard — detail panels | Poor | `CrewShowcasePanel.svelte` fake buttons; tabs lack arrow keys |
| Screen reader — announcements | Mixed | `GameToast`, `DialogBox`, `BattleHudPlate` context; gaps on loading, Deck Read |
| Focus visibility | Good / partial | `GameButton`, `CommandMenu`; **missing on `MoveMenu`** |
| Touch targets | Good | `GameButton` min-height 44px; design rule in `design.mdc` |
| Reduced motion | Good | CSS `@media (prefers-reduced-motion)` + `prefersReducedMotion` in JS |
| Color / typography | Unverified | Warm muted palette; small cabinet labels may fail size/contrast |
| Page structure | Weak | No `<main>` on game routes; no skip link |
| Text selection | Blocked | Global `user-select: none` in `app.css` |
| Automated testing | Missing | No axe, no a11y eslint beyond compiler |

---

## What is working (keep these patterns)

### Document and language

- `src/app.html`: `<html lang="en">`, viewport meta.

### Buttons and labels

- `GameButton.svelte`: native `<button>`, optional `aria-label`, `aria-pressed`, `:focus-visible` mustard ring, 44px min height.
- `FreeFormButton.svelte`: requires `ariaLabel` prop (typed).
- `SettingsNavButton.svelte` / `GuideNavButton.svelte`: icon buttons with descriptive `ariaLabel`; decorative labels `aria-hidden`.

### Dialog and toast

- `DialogBox.svelte`: typewriter respects `prefersReducedMotion`; `role="status"` + `aria-live="polite"` while typing; continue state becomes focusable `role="button"` with Enter/Space; `aria-label` reflects full text or action.
- `GameToast.svelte`: `role="alert"`, `aria-live="assertive"`.

### Modals (partial)

- `GameModal.svelte`: `role="dialog"`, `aria-modal="true"`, `aria-label`, initial focus on open, Escape closes.

### Data visualization labels

- `SegmentedHpBar.svelte`: `aria-label="{label} {current} of {max}"`.
- `XpProgressBar.svelte`: `aria-label="{label} progress"`.
- `PowerPips.svelte`: `role="img"` + `aria-label`.
- `BstRadarChart.svelte`: `role="img"` + `aria-label`.

### Battle keyboard model

- `BattleScene.svelte` `handleWindowKeydown`: command grid, move select, move learn, dialog advance, replay skip.
- `CommandMenu.svelte`: `$effect` syncs DOM focus to `selected` index.

### Reduced motion

- Widespread `@media (prefers-reduced-motion: reduce)` and `prefersReducedMotion.current` in hatch, crew, battle, dialog.

### Decorative hiding

- Bezel, film grain, cursors, type badges in dialog visual layer: `aria-hidden="true"`.

---

## Findings register

Each row maps to a fix plan. Severity: **H** high, **M** medium, **L** low.

| ID | Severity | Finding | Location | Plan |
| :--- | :--- | :--- | :--- | :--- |
| A11Y-001 | H | `role="button"` + `tabindex="0"` without `onkeydown` or `aria-label` | `CrewShowcasePanel.svelte` HP/XP rows | 01 |
| A11Y-002 | H | Tab pattern missing `aria-controls`, `id`, arrow keys, `aria-labelledby` | `CrewShowcasePanel.svelte`, `HatchCandidatePanel.svelte` | 02 |
| A11Y-003 | H | Modal: no focus trap, no focus restore on close | `GameModal.svelte` | 03 |
| A11Y-004 | H | Battle menus: window-key nav vs Tab focus desync; `MoveMenu` no focus sync/styles | `BattleScene.svelte`, `MoveMenu.svelte`, `MoveLearnMenu.svelte` | 04 |
| A11Y-005 | H | Deck Read (`hold C`) keyboard-only; no touch/screen reader path | `BattleScene.svelte`, `BattleHudPlate.svelte`, `MoveMenu.svelte`, `DESIGN.md` §9.2 | 05 |
| A11Y-006 | M | No `<main>`, skip link, or route-level heading on most pages | routes, `SceneFrame.svelte` | 06 |
| A11Y-007 | H | Global `user-select: none` on `*` | `app.css` | 07 |
| A11Y-008 | M | `role="menu"` on non-menu widgets | `CommandMenu`, `MoveMenu`, `TitleScene`, `SettingsModal`, `CrewFormationMenu` | 08 |
| A11Y-009 | M | Loading/async text not in live regions | `BattleScene.svelte`, others | 09 |
| A11Y-010 | M | Battle/crew sprites `alt=""` where name is available | `BattleMon.svelte`, roster scenes | 10 |
| A11Y-011 | M | Disabled settings options silent to keyboard users | `SettingsModal.svelte` | 10 |
| A11Y-012 | L | `MoveLearnMenu` decline button: no `:focus-visible` | `MoveLearnMenu.svelte` | 10 |
| A11Y-013 | L | `ElementBadge` is unlabeled span (text content OK when inline) | `ElementBadge.svelte` | — |
| A11Y-014 | — | No axe/contrast CI | — | 11 |
| A11Y-015 | L | Intentional `svelte-ignore a11y_no_noninteractive_tabindex` (2) | `DialogBox`, `GameModal` | 03, documented |

---

## Compiler and lint posture

```json
// vibemon/frontend/package.json — only static check today
"check": "svelte-kit sync && svelte-check --tsconfig ./tsconfig.json"
```

- No `eslint-plugin-svelte` a11y rules in CI.
- Suppressed warnings are documented in A11Y-015; do not add new suppressions without pairing keyboard behavior.

---

## WCAG 2.2 mapping (target level AA)

Not a formal audit; indicative gaps:

| Criterion | Status | Notes |
| :--- | :--- | :--- |
| 1.1.1 Non-text Content | Partial | Scene bg alts good; battle sprites empty |
| 1.3.1 Info and Relationships | Partial | Tabs/menus incomplete |
| 1.4.3 Contrast (Minimum) | Unknown | Needs measured audit (Plan 11) |
| 1.4.4 Resize text | OK | clamp() typography |
| 1.4.10 Reflow | OK | mobile viewport guide exists |
| 2.1.1 Keyboard | Partial | Game flows OK; fake buttons fail |
| 2.1.2 No Keyboard Trap | Partial | Modals leak focus |
| 2.4.3 Focus Order | Partial | Battle dual model |
| 2.4.7 Focus Visible | Partial | Move menu gap |
| 2.5.5 Target Size | Good | 44px floor on primary buttons |
| 3.2.4 Consistent Identification | OK | Settings/Guide knobs consistent |
| 4.1.2 Name, Role, Value | Partial | Tabs, fake buttons |
| 4.1.3 Status Messages | Partial | Toasts good; loading gaps |

---

## Out of scope (explicit)

- **Gamepad API** — design mentions gamepad; not implemented; separate plan if needed.
- **Full WCAG certification** — plans target practical player access, not legal sign-off.
- **Backend API accessibility** — this audit is frontend-only.
- **Internationalization / `lang` dynamism** — English-only for now.
