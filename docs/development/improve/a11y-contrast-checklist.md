# Accessibility contrast checklist

**Status:** Template — fill during Plan 11 Part D.  
**Tooling:** [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/), Chrome DevTools → Accessibility → Contrast.  
**Targets:** WCAG 2.2 Level AA — 4.5:1 normal text, 3:1 large text (≥18pt / 14pt bold) and UI components.

Record **measured ratio**, **pass/fail**, and **fix** if failing.

---

## Core UI surfaces

| ID | Foreground | Background | Token / usage | Size | Ratio | AA | Fix |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-01 | `#3D2B1F` | `#F0E7CE` | Dialog text on parchment | body | | | |
| C-02 | `#3D2B1F` | `--vm-panel-command-bg` | Command menu labels | ~13px | | | |
| C-03 | `#C0542A` | `--vm-panel-command-bg` | Selected command (burnt orange) | ~13px | | | |
| C-04 | `#3D2B1F` | `--vm-panel-status-bg` | Status panel / HUD | body | | | |
| C-05 | `#C9A23F` | `--vm-tobacco-black` / bezel | Focus ring (component) | 2px UI | | 3:1 | |
| C-06 | `--vm-parchment` | `--vm-cabinet-wood` | Settings knob label | 8px caps | | | |
| C-07 | `--vm-tobacco` 78% + plum | `--vm-cabinet-guide-surface` | Guide panel labels | ~7–9px | | | |
| C-08 | `#3D2B1F` | `--vm-cabinet-guide-surface` | Guide panel values | caption | | | |

---

## Status / HP

| ID | Foreground | Background | Usage | Ratio | AA | Fix |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C-10 | `#6B9B5A` (Sage) | command/parchment | HP segments healthy | | | |
| C-11 | `#CC7A22` (Amber) | command/parchment | HP caution | | | |
| C-12 | `#A03020` (Brick) | command/parchment | HP critical | | | |

---

## Element badges (worst-case sample)

Sample the **lowest-contrast** types after measurement; full 18-type matrix optional.

| Type | BG (`COLORS.md`) | FG (badge text) | Ratio | AA | Fix |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Electric | `#D4A017` | tobacco/parchment | | | |
| Ghost | `#524870` | parchment | | | |
| Steel | `#8A8C8E` | tobacco | | | |
| … | | | | | |

---

## Focus and interactive states

| ID | State | Ratio | AA | Notes |
| :--- | :--- | :--- | :--- | :--- |
| F-01 | `:focus-visible` mustard on command cell | | 3:1 UI | |
| F-02 | `:focus-visible` on dialog continue | | 3:1 UI | |
| F-03 | Disabled settings panel opacity 0.48 | | | Informational only — pair with footnote (Plan 10) |

---

## Known risks (pre-audit)

From static review — verify or dismiss:

1. **Cabinet guide labels** at `clamp(0.4375rem, …)` — may fail size + contrast.
2. **Mustard cursor** on parchment dialog — decorative; not required to meet text contrast if accompanied by text label.
3. **Selected move/command** orange on warm panel — verify against `#F0E7CE` mix.

---

## Sign-off

| Role | Name | Date |
| :--- | :--- | :--- |
| Measured by | | |
| Reviewed by | | |
| Exceptions documented in | `tests/a11y/allowed-violations.json` | |
