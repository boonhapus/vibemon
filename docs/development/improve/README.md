# Frontend improvement plans

Tracked follow-up work that is not yet canonical in `DESIGN.md` or an ADR. Each plan is self-contained with goal, scope, implementation steps, and acceptance checks.

## Accessibility (`a11y-*`)

Audit baseline and phased fix plans from the June 2026 frontend accessibility review.

| Order | Plan | Severity | Est. effort | Depends on |
| :--- | :--- | :--- | :--- | :--- |
| — | [a11y-audit-baseline.md](./a11y-audit-baseline.md) | — | read-only | — |
| 1 | [a11y-plan-01-fake-buttons-and-hints.md](./a11y-plan-01-fake-buttons-and-hints.md) | High | S | — |
| 2 | [a11y-plan-02-tab-pattern.md](./a11y-plan-02-tab-pattern.md) | High | M | — |
| 3 | [a11y-plan-03-modal-focus-management.md](./a11y-plan-03-modal-focus-management.md) | High | M | — |
| 4 | [a11y-plan-04-battle-menu-input.md](./a11y-plan-04-battle-menu-input.md) | High | M | 03 (optional) |
| 5 | [a11y-plan-05-deck-read-alternative.md](./a11y-plan-05-deck-read-alternative.md) | High | L | 04 |
| 6 | [a11y-plan-06-landmarks-and-page-structure.md](./a11y-plan-06-landmarks-and-page-structure.md) | Medium | S | — |
| 7 | [a11y-plan-07-text-selection-scope.md](./a11y-plan-07-text-selection-scope.md) | High | S | — |
| 8 | [a11y-plan-08-menu-role-semantics.md](./a11y-plan-08-menu-role-semantics.md) | Medium | S | 04 |
| 9 | [a11y-plan-09-live-regions-async-states.md](./a11y-plan-09-live-regions-async-states.md) | Medium | S | — |
| 10 | [a11y-plan-10-sprite-alt-and-visual-polish.md](./a11y-plan-10-sprite-alt-and-visual-polish.md) | Medium | S | — |
| 11 | [a11y-plan-11-automated-testing-and-contrast.md](./a11y-plan-11-automated-testing-and-contrast.md) | Process | M | 01–10 (incremental) |
| — | [a11y-contrast-checklist.md](./a11y-contrast-checklist.md) | — | fill in Plan 11 | — |

**Effort key:** S = small (≤1 day), M = medium (2–3 days), L = large (4+ days or design touch).

### Recommended PR slicing

Keep reviews small and verifiable:

1. **PR A — Hint controls:** Plan 01 only.
2. **PR B — Tabs:** Plan 02 (+ shared `TabStrip` helper if extracted).
3. **PR C — Modals:** Plan 03 (benefits Settings, Provider config, Adopt crew, Mobile viewport guide).
4. **PR D — Battle menus:** Plans 04 + 08 together (same files).
5. **PR E — Deck Read:** Plan 05 (+ `DESIGN.md` §9.2 update).
6. **PR F — Structure & copy:** Plans 06 + 07.
7. **PR G — Polish:** Plans 09 + 10.
8. **PR H — CI:** Plan 11 (axe + contrast checklist; can land early with smoke routes only).

### Verification commands (frontend)

```bash
cd vibemon/frontend
pnpm check          # svelte-check / compile-time a11y hints
pnpm test           # unit tests (add a11y-related tests per plan)
pnpm build          # ensure no SSR regressions on aria attrs
```

Manual smoke (every PR touching UI):

- `/` — title menu keyboard + Tab
- `/register` — name input, Tab order
- `/deck/crew` — showcase tabs, hint buttons
- `/battle/{id}` — command grid, move grid, dialog continue, Escape
- `/styleguide` — focus rings visible on all button specimens

Screen reader spot-check (NVDA on Windows or VoiceOver on macOS): one pass after PR C and PR D.

### Related docs

- `docs/development/DESIGN.md` — §5.4 touch targets, §9 battle UX (Deck Read)
- `docs/development/COLORS.md` — contrast audit palette
- `.cursor/rules/design.mdc` — `--anim-*`, `prefersReducedMotion`, 44px touch floor
