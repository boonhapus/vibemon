# P1-T7 — Frontend Scaffold & Location Flow

**Phase:** 1 — Core Pipeline
**Dependencies:** P1-T1 (backend must be running), P1-T6
**Depends on this:** P2-T1, P3-T1, P4-T1

---

## Objective

Create the SvelteKit SPA skeleton with a landing page that collects the user's location (via browser Geolocation API or manual city input), posts to the backend, and logs the returned JSON payload.

## Important

Use **Svelte 5 syntax only** (see AGENTS.md): `$state()`, `$derived()`, `$effect()`, `$props()`. Do not use `export let`, `writable()`, or slot-based patterns.

## Tasks

1. **Initialise the frontend project**
   - `npx sv create frontend` (SvelteKit with TypeScript)
   - Configure `adapter-static` for pure SPA output
   - Set up `pnpm` as package manager
   - Add proxy config for `/api` → `http://localhost:8000` in `vite.config.ts`

2. **Define TypeScript types**
   - `frontend/src/lib/types.ts`
   - Mirror all backend models: `VibemonStats`, `VisualDNA`, `Move`, `VibemonPayload`, `GenerateResponse`
   - Use TypeScript interfaces/types, matching the JSON keys from the backend

3. **Build the landing page (`/`)**
   - `frontend/src/routes/+page.svelte`
   - Request browser geolocation on page load
   - If denied, show a text input for city name
   - "Generate" button that POSTs to `/api/v1/generate` with `user_id`, `latitude`, `longitude`, `auth_tokens: {}`
   - On success: store response in a module-level `$state` and navigate to `/battle`
   - On 422: show location prompt
   - Display loading spinner during the request

4. **Create a shared state module for the generation result**
   - `frontend/src/lib/stores/generation.ts`
   - Export a `$state`-backed object holding the `GenerateResponse`
   - The battle page will read from this

5. **Create a placeholder battle page**
   - `frontend/src/routes/battle/+page.svelte`
   - Read from the generation store
   - If no data, redirect back to `/`
   - For now: display the raw JSON payload formatted on screen

6. **Add basic global styles**
   - Dark theme background, centered layout
   - System font stack

## Acceptance Criteria

- `pnpm dev` starts without error
- Clicking "Generate" with browser location sends a valid POST, receives a response, and navigates to `/battle`
- The raw JSON of both player and enemy payloads is visible on the battle page
- City name fallback input appears if geolocation is denied

## Files Created

```
frontend/
  svelte.config.js
  vite.config.ts
  src/
    routes/
      +page.svelte
      battle/+page.svelte
    lib/
      types.ts
      stores/generation.ts
    app.css
```
