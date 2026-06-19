# Plan 11 — Automated testing and contrast audit

**Findings:** A11Y-014  
**Severity:** Process (enables regression prevention)  
**Effort:** M (2–3 days initial setup)  
**Primary files:**

- `vibemon/frontend/package.json`
- **New:** `vibemon/frontend/tests/a11y/` or extend Playwright if present
- **New:** `docs/development/improve/a11y-contrast-checklist.md` (generated findings)
- `.agents/skills/development/playwright-cli/SKILL.md` — use if browser automation added

---

## Goal

1. **Automated** accessibility checks on critical routes in CI.
2. **Manual contrast checklist** against locked palette (`COLORS.md`).
3. **Definition of done** for future UI PRs.

---

## Part A — axe-core in Vitest or Playwright

### Decision: Playwright + @axe-core/playwright

Vitest + jsdom misses focus trap and real contrast. Playwright matches production DOM + CSS.

If repo has no Playwright yet:

```bash
cd vibemon/frontend
pnpm add -D @playwright/test @axe-core/playwright
npx playwright install chromium
```

**New script** in `package.json`:

```json
"test:a11y": "playwright test tests/a11y"
```

### Smoke routes

| Test file | URL | Waits for |
| :--- | :--- | :--- |
| `title.spec.ts` | `/` | title menu visible |
| `register.spec.ts` | `/register` | username input (may need dev auth bypass) |
| `crew.spec.ts` | `/deck/crew` | requires session — use test fixture or mock |
| `battle.spec.ts` | `/battle/test-id` | requires API — stub or dev battle seed |

**ponytail:** start with **title + styleguide** only (no auth); expand as test harness matures.

Example:

```typescript
// tests/a11y/title.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('title screen a11y', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Title menu' }).waitFor();
  const results = await new AxeBuilder({ page })
    .disableRules(['color-contrast']) // handle in manual checklist initially
    .analyze();
  expect(results.violations).toEqual([]);
});
```

### CI integration

Add job step after `pnpm build`:

```yaml
- run: pnpm exec playwright test tests/a11y --project=chromium
```

Or mark `continue-on-error: true` until Plans 01–10 land — document baseline violation count.

### Violation triage

Track allowed exceptions in `tests/a11y/allowed-violations.json` with ticket ids — shrink over time.

---

## Part B — svelte-check a11y warnings

Already clean. Add CI gate:

```bash
pnpm check
```

On PR template: "If you add `svelte-ignore a11y_*`, link to plan or justify."

Optional: enable stricter svelte compiler options if added in future svelte-check releases.

---

## Part C — ESLint (optional, later)

`eslint-plugin-svelte` with `svelte3/recommended` a11y rules — duplicates compiler; **defer** unless team wants pre-commit lint beyond check.

---

## Part D — Manual contrast audit

Create **`a11y-contrast-checklist.md`** after running tool (Chrome DevTools Accessibility, [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)).

### Required pairings (WCAG AA 4.5:1 normal text, 3:1 large)

| Foreground | Background | Context | Pass? |
| :--- | :--- | :--- | :--- |
| `#3D2B1F` (Tobacco) | `#F0E7CE` (Parchment) | Dialog body | TBD |
| `#3D2B1F` | command panel bg token | Menu cells | TBD |
| `#C9A23F` (Mustard) | `#2A1E16` / bezel dark | Focus ring | TBD (UI component, 3:1) |
| Cabinet guide label | guide surface | `--vm-font-ui` 7px effective | Likely fail — document |
| Burnt orange selected command | command bg | Selected menu label | TBD |
| Element badges | each type color × badge fg | 18 types | sample worst |

### Small text risk

`CabinetGuidePanel.svelte` labels:

```css
font-size: clamp(0.4375rem, 1.4vw, 0.5625rem);
```

If contrast fails:

- Bump minimum to `0.5625rem` (9px) **or**
- Lighten `--vm-tobacco` mix on guide labels **or**
- Accept as decorative (not primary info) — document in checklist

### Status HP colors

Sage / Amber / Brick on parchment/command surfaces — verify segmented bar labels.

---

## Part E — PR checklist (add to improve/README or CONTRIBUTING)

```markdown
### UI accessibility checklist
- [ ] Focus visible on new interactive elements (`:focus-visible`)
- [ ] Icon buttons have accessible name
- [ ] No `role="button"` on div without keyboard handlers
- [ ] Async/loading text uses live region or toast
- [ ] `pnpm check` clean
- [ ] axe smoke tests pass (or violation count not increased)
```

---

## Part F — Manual screen reader script

Quarterly or before release:

1. Title → Register → name input → submit flow.
2. Battle → command → move → dialog advance.
3. Crew → tabs → hint button → story selection.
4. Settings modal → Escape → focus restore.

Log issues in GitHub with `a11y` label.

---

## Milestones

| Milestone | Deliverable |
| :--- | :--- |
| M1 | Playwright + axe on `/` and `/styleguide` in CI |
| M2 | Contrast checklist filled for core HUD tokens |
| M3 | axe on `/deck/crew` with test auth fixture |
| M4 | axe on battle with dev battle seed |
| M5 | Zero allowed violations without ticket |

---

## Acceptance criteria

- [ ] `pnpm test:a11y` runs locally and in CI.
- [ ] Title route axe scan passes (or documented exceptions).
- [ ] `a11y-contrast-checklist.md` exists with ≥10 pairings measured.
- [ ] PR checklist published in `improve/README.md`.
- [ ] Team agrees violation baseline policy.

---

## Non-goals

- Full manual WCAG audit certification.
- Pa11y, Lighthouse CI duplication (pick one tool — axe sufficient).

---

## Dependencies

Install Playwright only if not already in monorepo — check root CI yaml before adding duplicate browser caches.
