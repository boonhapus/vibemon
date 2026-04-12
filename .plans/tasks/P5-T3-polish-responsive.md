# P5-T3 — UI Polish, Error States & Responsive Design

**Phase:** 5 — GitHub Integration and Polish
**Dependencies:** P4-T3, P5-T2
**Depends on this:** —

---

## Objective

Bring the application to production quality: polished auth screen design, comprehensive error and loading states, flavour text display, and a fully responsive mobile layout.

## Tasks

1. **Auth screen visual design**
   - Dark theme with subtle gradient or particle background
   - App logo / title treatment for "Vibemon"
   - Provider connect buttons styled as cards with provider logos (Spotify green, GitHub dark)
   - Connected state: card shows checkmark, username, subtle glow
   - Location status indicator: "📍 London, UK" or "📍 Enter your city"
   - "Generate" button with loading state (spinner + "Creating your Vibemon...")
   - "Play as Guest" as a secondary/text-style button

2. **Error states**
   - **API failure**: Toast or inline error: "Something went wrong. Try again."
   - **Location denied + no city**: Prompt with city input field and clear explanation
   - **Invalid city**: "Couldn't find that city. Try a nearby larger city."
   - **OAuth failure**: "Couldn't connect to {provider}. Try again or play as guest."
   - **Network offline**: Detect with `navigator.onLine` and show a banner
   - All errors dismissible, non-blocking where possible

3. **Loading states**
   - Generation request: full-screen overlay with animated Vibemon silhouette or pulsing blob
   - Battle page: skeleton UI while initialising battle state
   - Move execution: brief "thinking" indicator during enemy turn delay

4. **Flavour text in battle UI**
   - Display `flavour_text` from the player's `VibemonPayload` where the layout leaves room (e.g. footer or card footnote)
   - Truncate with ellipsis if too long; expand on tap/click

5. **Mobile-responsive layout**
   - Auth screen: single column, full-width buttons
   - Battle screen: follow [.plans/vibemon-visual-design-system.md](../vibemon-visual-design-system.md) §9 — same 2×2 move grid invariant; adjust scene height, card `min-width`, and name font size at ≤560px
   - HP bars and log readable at narrow widths (collapsible log or compact strip if needed)
   - Touch targets ≥ 48px
   - Test at 375px (iPhone SE), 390px (iPhone 14), 768px (tablet)

6. **Accessibility basics**
   - Move buttons have `aria-label` with move name and power
   - HP bars have `role="progressbar"` with `aria-valuenow`/`aria-valuemax`
   - Focus management: focus moves to move buttons on player turn
   - Colour contrast: ensure text meets WCAG AA on dark background

7. **Final CSS cleanup**
   - Spacing, colour, motion tokens from `vibemon-visual-design-system.md` §5–§10 (`--sp-*`, `--vb-*`, `--r-*`, `--t-*`)
   - Remove any debug output or raw JSON displays

## Acceptance Criteria

- Auth screen looks polished and intentional, not like a prototype
- Every possible error state has a user-friendly message
- Loading states prevent user confusion during async operations
- Battle is fully playable on a 375px-wide screen
- No raw JSON, console.logs, or placeholder text visible to the user

## Files Modified

```
frontend/src/routes/+page.svelte
frontend/src/routes/battle/+page.svelte
frontend/src/app.css
frontend/src/lib/components/*.svelte (various)
```
